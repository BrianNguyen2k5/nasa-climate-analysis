from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


LOG_PATH = Path(__file__).resolve().parent.parent / "api" / "ai_chat_logs.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_sessions() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    try:
        return json.loads(LOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_sessions(sessions: list[dict[str, Any]]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")


def create_session(title: str = "Cuoc hoi thoai AI") -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "title": title[:80] or "Cuoc hoi thoai AI",
        "created_at": _now(),
        "updated_at": _now(),
        "messages": [],
    }


def append_message(
    session_id: str,
    role: str,
    content: str,
    **metadata: Any,
) -> list[dict[str, Any]]:
    sessions = load_sessions()
    session = next((item for item in sessions if item["id"] == session_id), None)
    if session is None:
        session = create_session(content)
        session["id"] = session_id
        sessions.insert(0, session)

    session["messages"].append(
        {
            "role": role,
            "content": content,
            "timestamp": _now(),
            **metadata,
        }
    )
    session["updated_at"] = _now()
    save_sessions(sessions)
    return sessions

