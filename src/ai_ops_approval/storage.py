from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_ops_approval.domain import Decision, RequestStatus, TriageResult


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


class RequestNotFoundError(LookupError):
    pass


class IdempotencyConflictError(ValueError):
    pass


class RequestFinalizedError(ValueError):
    pass


def payload_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RequestStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        if self.db_path.parent:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        try:
            yield conn
        except BaseException:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    requester TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    customer_tier TEXT NOT NULL,
                    amount_at_risk REAL NOT NULL,
                    metadata_json TEXT NOT NULL,
                    triage_json TEXT NOT NULL,
                    idempotency_key TEXT,
                    request_fingerprint TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            request_columns = {
                str(row["name"]) for row in conn.execute("PRAGMA table_info(requests)").fetchall()
            }
            if "idempotency_key" not in request_columns:
                conn.execute("ALTER TABLE requests ADD COLUMN idempotency_key TEXT")
            if "request_fingerprint" not in request_columns:
                conn.execute("ALTER TABLE requests ADD COLUMN request_fingerprint TEXT")
            self._backfill_request_fingerprints(conn)
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_requests_idempotency_key
                ON requests(idempotency_key)
                WHERE idempotency_key IS NOT NULL
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests(created_at DESC)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    FOREIGN KEY(request_id) REFERENCES requests(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decisions_request_id ON decisions(request_id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(request_id) REFERENCES requests(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_request_created
                ON audit_events(request_id, created_at DESC)
                """
            )

    def ping(self) -> None:
        with self.connect() as conn:
            conn.execute("SELECT 1").fetchone()

    def _backfill_request_fingerprints(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT id, title, description, requester, channel, customer_tier,
                   amount_at_risk, metadata_json
            FROM requests
            WHERE idempotency_key IS NOT NULL AND request_fingerprint IS NULL
            """
        ).fetchall()
        for row in rows:
            payload = {
                "title": row["title"],
                "description": row["description"],
                "requester": row["requester"],
                "channel": row["channel"],
                "customer_tier": row["customer_tier"],
                "amount_at_risk": float(row["amount_at_risk"]),
                "metadata": json.loads(row["metadata_json"]),
            }
            conn.execute(
                "UPDATE requests SET request_fingerprint = ? WHERE id = ?",
                (payload_fingerprint(payload), row["id"]),
            )

    def create_request(
        self,
        payload: dict[str, Any],
        triage: TriageResult,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if idempotency_key:
            existing = self.get_request_by_idempotency_key(idempotency_key, payload)
            if existing is not None:
                return existing

        request_id = str(uuid.uuid4())
        now = utcnow_iso()
        status = (
            RequestStatus.NEEDS_REVIEW if triage.requires_human_review else RequestStatus.RECEIVED
        )
        row = {
            "id": request_id,
            "status": status.value,
            "title": payload["title"],
            "description": payload["description"],
            "requester": payload.get("requester", "unknown"),
            "channel": payload.get("channel", "webhook"),
            "customer_tier": payload.get("customer_tier", "standard"),
            "amount_at_risk": float(payload.get("amount_at_risk") or 0),
            "metadata_json": json.dumps(payload.get("metadata", {}), ensure_ascii=True),
            "triage_json": json.dumps(triage_to_dict(triage), ensure_ascii=True),
            "idempotency_key": idempotency_key,
            "request_fingerprint": payload_fingerprint(payload) if idempotency_key else None,
            "created_at": now,
            "updated_at": now,
        }

        try:
            with self.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO requests (
                        id, status, title, description, requester, channel,
                        customer_tier, amount_at_risk, metadata_json, triage_json,
                        idempotency_key, request_fingerprint, created_at, updated_at
                    ) VALUES (
                        :id, :status, :title, :description, :requester, :channel,
                        :customer_tier, :amount_at_risk, :metadata_json, :triage_json,
                        :idempotency_key, :request_fingerprint, :created_at, :updated_at
                    )
                    """,
                    row,
                )
                self._insert_audit(
                    conn,
                    request_id,
                    "request_created",
                    {
                        "status": status.value,
                        "triage": triage_to_dict(triage),
                    },
                )
        except sqlite3.IntegrityError:
            if idempotency_key:
                existing = self.get_request_by_idempotency_key(idempotency_key, payload)
                if existing is not None:
                    return existing
            raise
        return self.get_request(request_id)

    def get_request_by_idempotency_key(
        self,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM requests WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if row is not None and payload is not None:
            stored_fingerprint = row["request_fingerprint"]
            if stored_fingerprint and stored_fingerprint != payload_fingerprint(payload):
                raise IdempotencyConflictError(
                    "Idempotency key was already used with a different request payload"
                )
        return request_row_to_dict(row) if row is not None else None

    def get_request(self, request_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM requests WHERE id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise RequestNotFoundError(request_id)
        return request_row_to_dict(row)

    def list_requests(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM requests"
        params: tuple[Any, ...] = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY created_at DESC LIMIT ?"
        params = (*params, limit)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [request_row_to_dict(row) for row in rows]

    def record_decision(
        self,
        request_id: str,
        decision: Decision,
        reviewer: str,
        notes: str,
    ) -> dict[str, Any]:
        new_status = {
            Decision.APPROVE: RequestStatus.APPROVED,
            Decision.REJECT: RequestStatus.REJECTED,
            Decision.REQUEST_CHANGES: RequestStatus.CHANGES_REQUESTED,
        }[decision]
        now = utcnow_iso()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                "SELECT status FROM requests WHERE id = ?",
                (request_id,),
            ).fetchone()
            if current is None:
                raise RequestNotFoundError(request_id)
            if current["status"] in {
                RequestStatus.APPROVED.value,
                RequestStatus.REJECTED.value,
            }:
                raise RequestFinalizedError(f"Request {request_id} is already finalized")

            conn.execute(
                """
                INSERT INTO decisions (request_id, decision, reviewer, notes, decided_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (request_id, decision.value, reviewer, notes, now),
            )
            conn.execute(
                """
                UPDATE requests SET status = ?, updated_at = ? WHERE id = ?
                """,
                (new_status.value, now, request_id),
            )
            self._insert_audit(
                conn,
                request_id,
                "human_decision_recorded",
                {
                    "decision": decision.value,
                    "reviewer": reviewer,
                    "notes": notes,
                    "new_status": new_status.value,
                },
            )
        return {
            "request_id": request_id,
            "status": new_status.value,
            "decision": decision.value,
            "reviewer": reviewer,
            "notes": notes,
            "decided_at": now,
        }

    def metrics(self) -> dict[str, Any]:
        with self.connect() as conn:
            status_rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM requests GROUP BY status"
            ).fetchall()
            category_rows = conn.execute(
                """
                SELECT json_extract(triage_json, '$.category') AS category, COUNT(*) AS count
                FROM requests
                GROUP BY category
                """
            ).fetchall()

        by_status = {str(row["status"]): int(row["count"]) for row in status_rows}
        by_category = {str(row["category"]): int(row["count"]) for row in category_rows}
        total_requests = sum(by_status.values())
        return {
            "total_requests": total_requests,
            "by_status": by_status,
            "by_category": by_category,
            "review_required": by_status.get(RequestStatus.NEEDS_REVIEW.value, 0),
            "approved": by_status.get(RequestStatus.APPROVED.value, 0),
            "rejected": by_status.get(RequestStatus.REJECTED.value, 0),
        }

    def audit_events(
        self,
        limit: int = 100,
        request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM audit_events"
        params: tuple[Any, ...] = ()
        if request_id:
            query += " WHERE request_id = ?"
            params = (request_id,)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params = (*params, limit)
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "id": int(row["id"]),
                "request_id": row["request_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _insert_audit(
        self,
        conn: sqlite3.Connection,
        request_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO audit_events (request_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (request_id, event_type, json.dumps(payload, ensure_ascii=True), utcnow_iso()),
        )


def triage_to_dict(triage: TriageResult) -> dict[str, Any]:
    return {
        "category": triage.category.value,
        "priority": triage.priority.value,
        "confidence": triage.confidence,
        "requires_human_review": triage.requires_human_review,
        "suggested_action": triage.suggested_action,
        "rationale": triage.rationale,
        "risk_flags": list(triage.risk_flags),
    }


def request_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "status": row["status"],
        "title": row["title"],
        "description": row["description"],
        "requester": row["requester"],
        "channel": row["channel"],
        "customer_tier": row["customer_tier"],
        "amount_at_risk": row["amount_at_risk"],
        "metadata": json.loads(row["metadata_json"]),
        "triage": json.loads(row["triage_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
