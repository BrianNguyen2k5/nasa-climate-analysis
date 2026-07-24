from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


PENDING_APPROVAL = "PENDING_APPROVAL"
FAILED = "FAILED"
SUCCESS = "SUCCESS"


@dataclass(frozen=True)
class ConversationTurn:
    request_id: str | None
    messages: tuple[dict[str, Any], ...]
    original_indexes: tuple[int, ...]
    latest_index: int
    has_pending_proposal: bool


def _request_id(message: dict[str, Any]) -> str | None:
    value = message.get("request_id")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _is_code_proposal(message: dict[str, Any]) -> bool:
    return bool(
        message.get("kind") == "code_proposal"
        or (
            message.get("role") == "assistant"
            and (message.get("current_code") or message.get("code"))
        )
    )


def build_conversation_turns(
    messages: Sequence[dict[str, Any]],
) -> list[ConversationTurn]:
    """Build display-only turns without mutating persisted messages."""
    grouped: dict[tuple[str, str | int], list[tuple[int, dict[str, Any]]]] = {}
    group_order: list[tuple[str, str | int]] = []
    active_group: tuple[str, str | int] | None = None

    def ensure_group(
        key: tuple[str, str | int],
    ) -> list[tuple[int, dict[str, Any]]]:
        if key not in grouped:
            grouped[key] = []
            group_order.append(key)
        return grouped[key]

    for index, message in enumerate(messages):
        request_id = _request_id(message)
        role = str(message.get("role") or "")

        if request_id is not None:
            key = ("request", request_id)
            ensure_group(key).append((index, message))
            active_group = key
            continue

        if role == "user":
            key = ("legacy", index)
            ensure_group(key).append((index, message))
            active_group = key
            continue

        if active_group is not None:
            ensure_group(active_group).append((index, message))
            continue

        key = ("orphan", index)
        ensure_group(key).append((index, message))

    turns: list[ConversationTurn] = []
    for key in group_order:
        indexed_messages = sorted(grouped[key], key=lambda item: item[0])
        indexes = tuple(index for index, _message in indexed_messages)
        turn_messages = tuple(message for _index, message in indexed_messages)
        turns.append(
            ConversationTurn(
                request_id=(
                    str(key[1]) if key[0] == "request" else None
                ),
                messages=turn_messages,
                original_indexes=indexes,
                latest_index=max(indexes),
                has_pending_proposal=any(
                    _is_code_proposal(message)
                    and message.get("status") == PENDING_APPROVAL
                    for message in turn_messages
                ),
            )
        )
    return turns


def sort_turns_newest_first(
    turns: Sequence[ConversationTurn],
) -> list[ConversationTurn]:
    return sorted(turns, key=lambda turn: turn.latest_index, reverse=True)


def build_answer_number_map(
    messages: Sequence[dict[str, Any]],
) -> dict[str, int]:
    """Keep assistant numbering tied to chronological storage order."""
    answer_numbers: dict[str, int] = {}
    answer_number = 0
    for message in messages:
        if message.get("role") != "assistant":
            continue
        answer_number += 1
        message_id = message.get("id")
        if message_id is not None:
            answer_numbers[str(message_id)] = answer_number
    return answer_numbers


def find_latest_assistant_answer_id(
    messages: Sequence[dict[str, Any]],
) -> str | None:
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        message_id = message.get("id")
        if message_id is not None:
            return str(message_id)
    return None


def should_expand_message(
    message: dict[str, Any],
    latest_answer_id: str | None,
) -> bool:
    if _is_code_proposal(message):
        status = str(message.get("status") or PENDING_APPROVAL)
        if status in {PENDING_APPROVAL, FAILED}:
            return True
        if status == SUCCESS:
            return str(message.get("id")) == latest_answer_id
        return False
    return str(message.get("id")) == latest_answer_id
