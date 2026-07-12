const state = {
  apiKey: sessionStorage.getItem("ai_ops_api_key") || "",
  authRequired: false,
  requests: [],
  metrics: null,
  audit: [],
  selectedId: null,
  activeView: "queue",
};

const elements = {};
let toastTimer;

document.addEventListener("DOMContentLoaded", async () => {
  Object.assign(elements, {
    authDialog: document.querySelector("#authDialog"),
    authForm: document.querySelector("#authForm"),
    authError: document.querySelector("#authError"),
    apiKeyInput: document.querySelector("#apiKeyInput"),
    clearKeyButton: document.querySelector("#clearKeyButton"),
    decisionDialog: document.querySelector("#decisionDialog"),
    decisionForm: document.querySelector("#decisionForm"),
    decisionError: document.querySelector("#decisionError"),
    decisionInput: document.querySelector("#decisionInput"),
    reviewerInput: document.querySelector("#reviewerInput"),
    notesInput: document.querySelector("#notesInput"),
    refreshButton: document.querySelector("#refreshButton"),
    authButton: document.querySelector("#authButton"),
    searchInput: document.querySelector("#searchInput"),
    statusFilter: document.querySelector("#statusFilter"),
    requestRows: document.querySelector("#requestRows"),
    queueEmpty: document.querySelector("#queueEmpty"),
    detailPanel: document.querySelector("#detailPanel"),
    auditRows: document.querySelector("#auditRows"),
    auditEmpty: document.querySelector("#auditEmpty"),
    auditCount: document.querySelector("#auditCount"),
    queueView: document.querySelector("#queueView"),
    auditView: document.querySelector("#auditView"),
    pageTitle: document.querySelector("#pageTitle"),
    toast: document.querySelector("#toast"),
  });

  bindEvents();
  refreshIcons();

  try {
    const config = await apiRequest("/config", { authenticated: false });
    state.authRequired = config.auth_required;
    if (state.authRequired && !state.apiKey) {
      openAuthDialog();
    } else {
      await refreshAll();
    }
  } catch (error) {
    setHealth(false, "API unavailable");
    showToast(error.message, true);
  }
});

function bindEvents() {
  elements.refreshButton.addEventListener("click", refreshAll);
  elements.authButton.addEventListener("click", openAuthDialog);
  elements.searchInput.addEventListener("input", renderRequests);
  elements.statusFilter.addEventListener("change", renderRequests);
  elements.authForm.addEventListener("submit", handleAuthSubmit);
  elements.clearKeyButton.addEventListener("click", clearApiKey);
  elements.decisionForm.addEventListener("submit", handleDecisionSubmit);

  document.querySelectorAll(".close-dialog").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog").close());
  });

  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });
}

async function apiRequest(path, options = {}) {
  const { authenticated = true, headers = {}, ...fetchOptions } = options;
  const requestHeaders = { ...headers };
  if (authenticated && state.apiKey) requestHeaders["X-API-Key"] = state.apiKey;
  if (fetchOptions.body && !requestHeaders["Content-Type"]) requestHeaders["Content-Type"] = "application/json";

  const response = await fetch(path, { ...fetchOptions, headers: requestHeaders });
  if (response.status === 401) {
    if (authenticated) openAuthDialog("The API key was rejected.");
    throw new Error("Authentication required");
  }

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === "object" && body?.detail ? body.detail : `Request failed (${response.status})`;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join(", ") : detail);
  }
  return body;
}

async function refreshAll() {
  elements.refreshButton.classList.add("loading");
  try {
    const [health, requests, metrics, audit] = await Promise.all([
      apiRequest("/health", { authenticated: false }),
      apiRequest("/requests?limit=500"),
      apiRequest("/metrics"),
      apiRequest("/audit?limit=200"),
    ]);
    state.requests = requests;
    state.metrics = metrics;
    state.audit = audit;
    setHealth(true, health.llm_mode === "openai" ? health.llm_model : "Deterministic triage");
    renderMetrics();
    renderRequests();
    renderRequestDetail();
    renderAudit();
  } catch (error) {
    if (error.message !== "Authentication required") {
      setHealth(false, "API unavailable");
      showToast(error.message, true);
    }
  } finally {
    elements.refreshButton.classList.remove("loading");
    refreshIcons();
  }
}

function renderMetrics() {
  const metrics = state.metrics || {};
  document.querySelector("#metricTotal").textContent = metrics.total_requests || 0;
  document.querySelector("#metricReview").textContent = metrics.review_required || 0;
  document.querySelector("#metricApproved").textContent = metrics.approved || 0;
  document.querySelector("#metricRejected").textContent = metrics.rejected || 0;
}

function renderRequests() {
  const search = elements.searchInput.value.trim().toLowerCase();
  const status = elements.statusFilter.value;
  const filtered = state.requests.filter((request) => {
    const searchable = `${request.title} ${request.description} ${request.requester} ${request.triage.category}`.toLowerCase();
    return (!search || searchable.includes(search)) && (!status || request.status === status);
  });

  elements.requestRows.innerHTML = filtered.map((request) => `
    <tr data-request-id="${escapeHtml(request.id)}" tabindex="0" class="${request.id === state.selectedId ? "selected" : ""}">
      <td><span class="request-title">${escapeHtml(request.title)}</span><span class="request-subtitle">${escapeHtml(request.requester)}</span></td>
      <td><span class="badge neutral">${escapeHtml(formatLabel(request.triage.category))}</span></td>
      <td><span class="badge priority-${escapeHtml(request.triage.priority)}">${escapeHtml(formatLabel(request.triage.priority))}</span></td>
      <td><span class="badge status-${escapeHtml(request.status)}">${escapeHtml(formatLabel(request.status))}</span></td>
      <td>${escapeHtml(formatRelativeTime(request.created_at))}</td>
    </tr>
  `).join("");

  elements.queueEmpty.hidden = filtered.length > 0;
  elements.requestRows.querySelectorAll("tr").forEach((row) => {
    const select = () => selectRequest(row.dataset.requestId);
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        select();
      }
    });
  });

  if (state.selectedId && !state.requests.some((request) => request.id === state.selectedId)) {
    state.selectedId = null;
    renderRequestDetail();
  }
}

function selectRequest(requestId) {
  state.selectedId = requestId;
  renderRequests();
  renderRequestDetail();
}

function renderRequestDetail() {
  const request = state.requests.find((item) => item.id === state.selectedId);
  if (!request) {
    elements.detailPanel.innerHTML = `<div class="detail-empty"><i data-lucide="mouse-pointer-2"></i><strong>Select a request</strong><span>Request context and decision controls appear here.</span></div>`;
    refreshIcons();
    return;
  }

  const isFinal = ["approved", "rejected"].includes(request.status);
  const risks = request.triage.risk_flags.length
    ? request.triage.risk_flags.map((flag) => `<span class="risk-chip">${escapeHtml(formatLabel(flag))}</span>`).join("")
    : `<span class="risk-chip">No explicit flags</span>`;

  elements.detailPanel.innerHTML = `
    <div class="detail-heading">
      <div><p class="eyebrow">Request detail</p><h2>${escapeHtml(request.title)}</h2><p class="detail-id">${escapeHtml(request.id)}</p></div>
      <button class="icon-button copy-button" type="button" aria-label="Copy request ID" title="Copy request ID"><i data-lucide="copy"></i></button>
    </div>
    <div class="detail-badges">
      <span class="badge priority-${escapeHtml(request.triage.priority)}">${escapeHtml(formatLabel(request.triage.priority))}</span>
      <span class="badge status-${escapeHtml(request.status)}">${escapeHtml(formatLabel(request.status))}</span>
      <span class="badge neutral">${Math.round(request.triage.confidence * 100)}% confidence</span>
    </div>
    <section class="detail-section"><h3>Description</h3><p>${escapeHtml(request.description)}</p></section>
    <section class="detail-section"><h3>Suggested action</h3><p>${escapeHtml(request.triage.suggested_action)}</p></section>
    <section class="detail-section"><h3>AI rationale</h3><p>${escapeHtml(request.triage.rationale)}</p></section>
    <section class="detail-section"><h3>Risk flags</h3><div class="risk-list">${risks}</div></section>
    <section class="detail-section detail-grid">
      <div><span>Requester</span><strong>${escapeHtml(request.requester)}</strong></div>
      <div><span>Channel</span><strong>${escapeHtml(request.channel)}</strong></div>
      <div><span>Customer tier</span><strong>${escapeHtml(request.customer_tier)}</strong></div>
      <div><span>Amount at risk</span><strong>${escapeHtml(formatAmount(request.amount_at_risk))}</strong></div>
    </section>
    <div class="detail-actions">
      <button class="button primary decision-button" type="button" ${isFinal ? "disabled" : ""}><i data-lucide="gavel"></i>${isFinal ? "Decision recorded" : "Record decision"}</button>
      <button class="button secondary quick-decision" data-decision="request_changes" type="button" ${isFinal ? "disabled" : ""}>Request changes</button>
      <button class="button danger quick-decision" data-decision="reject" type="button" ${isFinal ? "disabled" : ""}>Reject</button>
    </div>
  `;

  elements.detailPanel.querySelector(".copy-button").addEventListener("click", () => copyRequestId(request.id));
  elements.detailPanel.querySelector(".decision-button").addEventListener("click", () => openDecisionDialog("approve"));
  elements.detailPanel.querySelectorAll(".quick-decision").forEach((button) => {
    button.addEventListener("click", () => openDecisionDialog(button.dataset.decision));
  });
  refreshIcons();
}

function renderAudit() {
  elements.auditCount.textContent = `${state.audit.length} ${state.audit.length === 1 ? "event" : "events"}`;
  elements.auditRows.innerHTML = state.audit.map((event) => `
    <tr data-request-id="${escapeHtml(event.request_id)}">
      <td><span class="badge neutral">${escapeHtml(formatLabel(event.event_type))}</span></td>
      <td><code>${escapeHtml(event.request_id.slice(0, 12))}…</code></td>
      <td><span class="audit-detail">${escapeHtml(JSON.stringify(event.payload))}</span></td>
      <td>${escapeHtml(formatDateTime(event.created_at))}</td>
    </tr>
  `).join("");
  elements.auditEmpty.hidden = state.audit.length > 0;
  elements.auditRows.querySelectorAll("tr").forEach((row) => {
    row.addEventListener("click", () => {
      switchView("queue");
      selectRequest(row.dataset.requestId);
    });
  });
}

function switchView(view) {
  state.activeView = view;
  const isQueue = view === "queue";
  elements.queueView.hidden = !isQueue;
  elements.auditView.hidden = isQueue;
  elements.pageTitle.textContent = isQueue ? "Review queue" : "Audit log";
  document.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  refreshIcons();
}

function openAuthDialog(message = "") {
  elements.authError.textContent = message;
  elements.apiKeyInput.value = state.apiKey;
  if (!elements.authDialog.open) elements.authDialog.showModal();
  setTimeout(() => elements.apiKeyInput.focus(), 0);
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  state.apiKey = elements.apiKeyInput.value.trim();
  sessionStorage.setItem("ai_ops_api_key", state.apiKey);
  elements.authError.textContent = "";
  try {
    await apiRequest("/requests?limit=1");
    elements.authDialog.close();
    await refreshAll();
    showToast("API connected");
  } catch (error) {
    elements.authError.textContent = error.message;
  }
}

function clearApiKey() {
  state.apiKey = "";
  sessionStorage.removeItem("ai_ops_api_key");
  elements.apiKeyInput.value = "";
  elements.authError.textContent = state.authRequired ? "An API key is required by this server." : "";
}

function openDecisionDialog(decision) {
  if (!state.selectedId) return;
  elements.decisionInput.value = decision;
  elements.notesInput.value = "";
  elements.decisionError.textContent = "";
  elements.decisionDialog.showModal();
  setTimeout(() => elements.reviewerInput.focus(), 0);
}

async function handleDecisionSubmit(event) {
  event.preventDefault();
  if (!state.selectedId) return;
  elements.decisionError.textContent = "";
  const submitButton = elements.decisionForm.querySelector("button[type='submit']");
  submitButton.disabled = true;
  try {
    await apiRequest(`/requests/${encodeURIComponent(state.selectedId)}/decision`, {
      method: "POST",
      body: JSON.stringify({
        decision: elements.decisionInput.value,
        reviewer: elements.reviewerInput.value.trim(),
        notes: elements.notesInput.value.trim(),
      }),
    });
    elements.decisionDialog.close();
    await refreshAll();
    renderRequestDetail();
    showToast("Decision recorded");
  } catch (error) {
    elements.decisionError.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
}

function setHealth(online, label) {
  document.querySelector("#healthDot").className = `health-dot ${online ? "online" : "offline"}`;
  document.querySelector("#healthLabel").textContent = online ? "API online" : "API offline";
  document.querySelector("#modelLabel").textContent = label;
}

async function copyRequestId(requestId) {
  try {
    await navigator.clipboard.writeText(requestId);
    showToast("Request ID copied");
  } catch {
    showToast("Clipboard access unavailable", true);
  }
}

function showToast(message, isError = false) {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.className = `toast visible${isError ? " error" : ""}`;
  toastTimer = setTimeout(() => { elements.toast.className = "toast"; }, 2800);
}

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
}

function formatLabel(value) {
  return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatAmount(value) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function formatRelativeTime(value) {
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  const absolute = Math.abs(seconds);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (absolute < 60) return formatter.format(seconds, "second");
  if (absolute < 3600) return formatter.format(Math.round(seconds / 60), "minute");
  if (absolute < 86400) return formatter.format(Math.round(seconds / 3600), "hour");
  return formatter.format(Math.round(seconds / 86400), "day");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[character]);
}
