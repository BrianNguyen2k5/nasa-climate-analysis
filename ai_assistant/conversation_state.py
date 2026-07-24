from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, MutableMapping

from .code_sanitizer import validate_ai_edit_for_application


CODE_PROPOSAL_KIND = "code_proposal"
PENDING_APPROVAL = "PENDING_APPROVAL"
APPROVED_AND_EXECUTING = "APPROVED_AND_EXECUTING"
SUCCESS = "SUCCESS"
FAILED = "FAILED"
PROMPT_WIDGET_KEY = "ai_prompt_box"
PROMPT_RESET_PENDING_KEY = "ai_prompt_reset_pending"

TRANSIENT_KEYS = {
    "ai_pending_code",
    "ai_pending_answer",
    "ai_last_result",
    "ai_chart_conclusion",
    "ai_code_editor",
    "ai_fix_instruction",
    PROMPT_WIDGET_KEY,
    PROMPT_RESET_PENDING_KEY,
    "active_proposal_message_id",
    "ai_requested_session_id",
}
TRANSIENT_KEY_PREFIXES = (
    "ai_code_editor_",
    "ai_fix_instruction_",
    "ai_run_code_",
    "ai_request_fix_",
    "ai_conclude_chart_",
    "ai_activate_proposal_",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def code_sha256(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def create_code_proposal_message(
    answer: str,
    code: str,
    **metadata: Any,
) -> dict[str, Any]:
    created_at = _now_iso()
    message = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "kind": CODE_PROPOSAL_KIND,
        "content": answer,
        "answer": answer,
        "original_code": code,
        "current_code": code,
        "code": code,
        "revision": 1,
        "status": PENDING_APPROVAL,
        "result": None,
        "error": None,
        "conclusion": None,
        "chart_metadata": None,
        "created_at": created_at,
        "timestamp": created_at,
        "approved_at": None,
        "approved_code_hash": None,
        "executed_code": None,
        "executed_code_hash": None,
        "edit_history": [],
    }
    message.update(metadata)
    return message


def _stable_legacy_id(message: dict[str, Any], index: int) -> str:
    serialized = json.dumps(message, ensure_ascii=False, sort_keys=True, default=str)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"legacy-ai-message:{index}:{serialized}"))


def is_code_proposal(message: dict[str, Any]) -> bool:
    return bool(
        message.get("kind") == CODE_PROPOSAL_KIND
        or (
            message.get("role") == "assistant"
            and (message.get("current_code") or message.get("code"))
        )
    )


def normalize_message(message: dict[str, Any], index: int = 0) -> dict[str, Any]:
    normalized = dict(message)
    if not normalized.get("id"):
        normalized["id"] = _stable_legacy_id(normalized, index)
    normalized.setdefault("created_at", normalized.get("timestamp") or _now_iso())

    if not is_code_proposal(normalized):
        normalized.setdefault("kind", "text")
        return normalized

    code = str(normalized.get("current_code") or normalized.get("code") or "")
    answer = str(normalized.get("answer") or normalized.get("content") or "")
    status = str(normalized.get("status") or PENDING_APPROVAL)
    legacy_result = normalized.get("result")
    normalized.update(
        {
            "kind": CODE_PROPOSAL_KIND,
            "answer": answer,
            "content": normalized.get("content", answer),
            "original_code": str(normalized.get("original_code") or code),
            "current_code": code,
            "code": code,
            "revision": int(normalized.get("revision") or 1),
            "status": status,
            "result": legacy_result,
            "error": normalized.get("error"),
            "conclusion": normalized.get("conclusion"),
            "chart_metadata": normalized.get("chart_metadata"),
            "approved_at": normalized.get("approved_at"),
            "approved_code_hash": normalized.get("approved_code_hash"),
            "executed_code": normalized.get("executed_code")
            or (code if status == SUCCESS else None),
            "executed_code_hash": normalized.get("executed_code_hash"),
            "edit_history": list(normalized.get("edit_history") or []),
        }
    )
    if status == FAILED and not normalized.get("error"):
        if isinstance(legacy_result, dict):
            normalized["error"] = legacy_result.get("message")
        normalized["error"] = normalized.get("error") or normalized.get("content")
    return normalized


def normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_message(message, index) for index, message in enumerate(messages)]


def find_message_by_id(
    messages: list[dict[str, Any]],
    message_id: str,
) -> dict[str, Any] | None:
    return next((message for message in messages if message.get("id") == message_id), None)


def latest_code_proposal_id(messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(messages):
        if is_code_proposal(message):
            return str(message["id"])
    return None


def update_proposal_code(
    messages: list[dict[str, Any]],
    message_id: str,
    code: str,
    *,
    edit_instruction: str = "",
    edit_answer: str = "",
    increment_revision: bool = False,
) -> dict[str, Any]:
    message = find_message_by_id(messages, message_id)
    if message is None or not is_code_proposal(message):
        raise KeyError(f"Không tìm thấy code proposal: {message_id}")

    message["current_code"] = code
    message["code"] = code
    message["status"] = PENDING_APPROVAL
    message["result"] = None
    message["error"] = None
    message["conclusion"] = None
    message["chart_metadata"] = None
    message["approved_at"] = None
    message["approved_code_hash"] = None
    message["executed_code"] = None
    message["executed_code_hash"] = None
    if increment_revision:
        message["revision"] = int(message.get("revision") or 1) + 1
    if edit_instruction or edit_answer:
        history = list(message.get("edit_history") or [])
        history.append(
            {
                "instruction": edit_instruction,
                "answer": edit_answer,
                "code": code,
                "created_at": _now_iso(),
            }
        )
        message["edit_history"] = history
    return message


def resolve_ai_edit_source(
    message: dict[str, Any],
    editor_code: str,
) -> str:
    if not is_code_proposal(message):
        raise ValueError("AI edit source phải thuộc một code proposal.")
    return str(editor_code)


def apply_ai_edit_response(
    messages: list[dict[str, Any]],
    message_id: str,
    response_code: str,
    *,
    edit_instruction: str,
    edit_answer: str,
    source_code: str | None = None,
) -> tuple[dict[str, Any], bool]:
    message = find_message_by_id(messages, message_id)
    if message is None or not is_code_proposal(message):
        raise KeyError(f"Không tìm thấy code proposal: {message_id}")

    candidate = str(response_code or "").strip()
    source = (
        str(source_code)
        if source_code is not None
        else str(message.get("current_code") or "")
    )
    validation = validate_ai_edit_for_application(
        source,
        candidate,
        edit_instruction,
    )
    if not validation.valid:
        return message, False

    return (
        update_proposal_code(
            messages,
            message_id,
            candidate,
            edit_instruction=edit_instruction,
            edit_answer=edit_answer,
            increment_revision=True,
        ),
        True,
    )


def mark_proposal_approved(
    messages: list[dict[str, Any]],
    message_id: str,
    approved_code: str,
) -> dict[str, Any]:
    message = update_proposal_code(messages, message_id, approved_code)
    message["status"] = APPROVED_AND_EXECUTING
    message["approved_at"] = _now_iso()
    message["approved_code_hash"] = code_sha256(approved_code)
    return message


def attach_execution_result(
    messages: list[dict[str, Any]],
    message_id: str,
    *,
    executed_code: str,
    ok: bool,
    result: dict[str, Any] | None,
    error: str | None,
    chart_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message = find_message_by_id(messages, message_id)
    if message is None or not is_code_proposal(message):
        raise KeyError(f"Không tìm thấy code proposal: {message_id}")

    executed_hash = code_sha256(executed_code)
    if message.get("approved_code_hash") != executed_hash:
        raise ValueError("Code được thực thi không khớp code đã duyệt.")

    message["executed_code"] = executed_code
    message["executed_code_hash"] = executed_hash
    message["status"] = SUCCESS if ok else FAILED
    message["result"] = result if ok else None
    message["error"] = None if ok else (error or "Thực thi code thất bại.")
    message["chart_metadata"] = chart_metadata if ok else None
    return message


def attach_chart_conclusion(
    messages: list[dict[str, Any]],
    message_id: str,
    conclusion: str,
    suggestions: list[str] | None = None,
) -> dict[str, Any]:
    message = find_message_by_id(messages, message_id)
    if message is None or not is_code_proposal(message):
        raise KeyError(f"Không tìm thấy code proposal: {message_id}")
    message["conclusion"] = conclusion
    message["conclusion_suggestions"] = suggestions or []
    return message


def proposal_ui_policy(status: str) -> dict[str, Any]:
    if status == SUCCESS:
        return {
            "label_prefix": "Xem kết quả code",
            "expanded": False,
            "show_editor": False,
            "show_edit_explanation": False,
        }
    if status == FAILED:
        return {
            "label_prefix": "Xem lỗi code",
            "expanded": True,
            "show_editor": True,
            "show_edit_explanation": True,
        }
    return {
        "label_prefix": "Xem câu trả lời AI",
        "expanded": True,
        "show_editor": True,
        "show_edit_explanation": True,
    }


def request_prompt_reset_on_rerun(state: MutableMapping[str, Any]) -> None:
    state[PROMPT_RESET_PENDING_KEY] = True


def apply_pending_prompt_reset(state: MutableMapping[str, Any]) -> bool:
    if not state.pop(PROMPT_RESET_PENDING_KEY, False):
        return False
    state[PROMPT_WIDGET_KEY] = ""
    return True


def reset_ai_transient_state(state: MutableMapping[str, Any]) -> None:
    for key in list(state):
        if key in TRANSIENT_KEYS or key.startswith(TRANSIENT_KEY_PREFIXES):
            state.pop(key, None)
