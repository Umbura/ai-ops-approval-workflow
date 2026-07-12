import pytest
from pydantic import ValidationError

from ai_ops_approval.settings import Settings


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("llm_mode", "invalid"),
        ("openai_timeout_seconds", 0),
        ("openai_timeout_seconds", 121),
        ("openai_max_output_tokens", 99),
        ("openai_max_output_tokens", 4_001),
    ],
)
def test_settings_reject_invalid_runtime_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: value})
