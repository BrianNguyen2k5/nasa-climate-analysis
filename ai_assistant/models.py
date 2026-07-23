from __future__ import annotations

import json
import mimetypes
import re
from dataclasses import dataclass
from typing import Callable, TypeVar

from .config import AIConfig
from .constants import OFFICIAL_REGIONS


@dataclass
class AIResponse:
    answer: str
    code: str = ""
    suggestions: list[str] | None = None
    chart_title: str = ""


@dataclass(frozen=True, repr=False)
class ModelAttempt:
    provider: str
    model: str
    key_source: str
    api_key: str

    def __repr__(self) -> str:
        return (
            "ModelAttempt("
            f"provider={self.provider!r}, "
            f"model={self.model!r}, "
            f"key_source={self.key_source!r}"
            ")"
        )


class ModelConfigurationError(RuntimeError):
    """Raised when no API key is configured for a provider."""


class ModelAttemptsExhaustedError(RuntimeError):
    """Raised after every deterministic retryable attempt has failed."""


T = TypeVar("T")


OFFICIAL_REGIONS_TEXT = ", ".join(OFFICIAL_REGIONS)

BASE_SYSTEM_PROMPT = f"""
Bạn là trợ lý AI phân tích dữ liệu khí hậu tích hợp trong dashboard Streamlit.
Quy tắc bắt buộc:
- Trả lời bằng tiếng Việt, rõ ràng, có số liệu nếu số liệu đến từ dataset/ngữ cảnh được cung cấp.
- Không bịa dữ liệu, không bịa hình ảnh, không tạo dataset giả.
- Không tiết lộ, không mô tả, không sinh lại code dashboard/group/project. Chỉ được sinh code phân tích ngắn chạy trên DataFrame `df` khi người dùng yêu cầu.
- Nếu sinh code, code phải dùng DataFrame `df` đã có sẵn và các biến đã được nạp sẵn: `pd`, `np`, `px`, `go`. Tuyệt đối không viết import. Code phải tạo biến `fig`. Khi lọc thành phố, dùng `location_name` với các giá trị đúng trong dataset như `Buon Ma Thuot`, `Ho Chi Minh City`, `Ha Noi`, `Da Nang`.
- Code phải có comment tiếng Việt giải thích thao tác chính.
- Không dùng import/from import, open, os, sys, subprocess, network request, đọc/ghi file, eval, exec. Không viết `import plotly.express as px` hoặc `import plotly.graph_objects as go` vì `px` và `go` đã có sẵn.
- Code sinh ra ở trạng thái chờ duyệt; con người có quyền sửa trước khi thực thi.
- Sáu vùng chính thức trong phạm vi AI là: {OFFICIAL_REGIONS_TEXT}. Chỉ dùng các tên này trong câu trả lời, bộ lọc và code sinh ra.
"""


def build_model_attempts(
    provider: str,
    config: AIConfig,
    *,
    primary_model: str | None = None,
    backup_model: str | None = None,
) -> list[ModelAttempt]:
    provider_norm = provider.strip().lower()
    if provider_norm == "groq":
        key_candidates = (
            ("primary", getattr(config, "groq_api_key", None)),
            ("backup", getattr(config, "groq_api_key_backup", None)),
        )
        if primary_model is None:
            primary_model = getattr(config, "groq_primary_model", "")
        if backup_model is None:
            backup_model = getattr(config, "groq_backup_model", "")
    elif provider_norm == "gemini":
        key_candidates = (
            ("primary", getattr(config, "gemini_api_key", None)),
            ("backup", getattr(config, "gemini_api_key_backup", None)),
        )
        if primary_model is None:
            primary_model = getattr(config, "gemini_primary_model", "")
        if backup_model is None:
            backup_model = getattr(config, "gemini_backup_model", "")
    else:
        raise ValueError(f"Provider không được hỗ trợ: {provider!r}")

    keys: list[tuple[str, str]] = []
    seen_keys: set[str] = set()
    for source, raw_key in key_candidates:
        api_key = str(raw_key or "").strip()
        if not api_key or api_key in seen_keys:
            continue
        seen_keys.add(api_key)
        keys.append((source, api_key))

    models: list[str] = []
    seen_models: set[str] = set()
    for raw_model in (primary_model, backup_model):
        model = str(raw_model or "").strip()
        if not model or model in seen_models:
            continue
        seen_models.add(model)
        models.append(model)

    attempts: list[ModelAttempt] = []
    seen_attempts: set[tuple[str, str]] = set()
    for key_source, api_key in keys:
        for model in models:
            identity = (api_key, model)
            if identity in seen_attempts:
                continue
            seen_attempts.add(identity)
            attempts.append(
                ModelAttempt(
                    provider=provider_norm,
                    model=model,
                    key_source=key_source,
                    api_key=api_key,
                )
            )
    return attempts


def is_retryable_provider_error(error: Exception) -> bool:
    if isinstance(error, (TypeError, ValueError)):
        return False
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True

    status_code = getattr(error, "status_code", None)
    if status_code is None:
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
    try:
        status = int(status_code) if status_code is not None else None
    except (TypeError, ValueError):
        status = None
    if status in {401, 404, 408, 429}:
        return True
    if status is not None and 500 <= status <= 599:
        return True

    class_name = type(error).__name__.lower()
    retryable_class_tokens = (
        "authentication",
        "permissiondenied",
        "ratelimit",
        "resourceexhausted",
        "notfound",
        "unavailable",
        "deadlineexceeded",
        "timeout",
        "apiconnection",
        "internalserver",
        "servererror",
    )
    if any(token in class_name for token in retryable_class_tokens):
        return True

    message = str(error).lower()
    retryable_message_tokens = (
        "invalid api key",
        "api key not valid",
        "api_key_invalid",
        "api key expired",
        "expired api key",
        "authentication failed",
        "quota exhausted",
        "quota exceeded",
        "resource exhausted",
        "rate limit",
        "model unavailable",
        "model not found",
        "model deprecated",
        "service unavailable",
        "temporarily unavailable",
        "timed out",
        "timeout",
    )
    return any(token in message for token in retryable_message_tokens)


def execute_model_attempts(
    provider: str,
    attempts: list[ModelAttempt],
    operation: Callable[[ModelAttempt], T],
) -> T:
    if not attempts:
        raise ModelConfigurationError(
            f"Chưa cấu hình API key cho provider {provider}."
        )

    for attempt in attempts:
        try:
            return operation(attempt)
        except Exception as error:
            if not is_retryable_provider_error(error):
                raise

    attempted = ", ".join(
        f"{attempt.key_source}:{attempt.model}" for attempt in attempts
    )
    raise ModelAttemptsExhaustedError(
        f"Provider {provider} không khả dụng sau các cấu hình: {attempted}."
    )


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _extract_python_code(text: str) -> str:
    triple_json_match = re.search(r'"code"\s*:\s*"""(.*?)"""', text, re.DOTALL)
    if triple_json_match:
        return triple_json_match.group(1).strip()
    fence_match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    return ""


def _strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()


def ask_groq(
    config: AIConfig,
    prompt: str,
    dataset_context: str,
    mode: str,
    extra_context: str = "",
    code_input: str = "",
) -> AIResponse:
    wants_code = mode in {"Sinh chart/code", "Sửa code"}
    primary_model = (
        config.groq_code_model if wants_code else config.groq_primary_model
    )
    attempts = build_model_attempts(
        "groq",
        config,
        primary_model=primary_model,
        backup_model=config.groq_backup_model,
    )
    if not attempts:
        return AIResponse(
            answer=(
                "Thiếu GROQ_API_KEY hoặc GROQ_API_KEY_BACKUP trong file .env "
                "nên chưa thể gọi Groq."
            ),
            suggestions=[
                "Thêm ít nhất một Groq API key vào .env",
                "Chạy lại Streamlit sau khi cập nhật biến môi trường",
            ],
        )

    from groq import Groq

    json_instruction = """
Trả về DUY NHẤT một JSON hợp lệ:
{
  "answer": "giải thích/kết luận/gợi ý bằng tiếng Việt",
  "code": "code Python nếu cần sinh hoặc sửa, ngược lại chuỗi rỗng",
  "chart_title": "tiêu đề biểu đồ nếu có",
  "suggestions": ["gợi ý 1", "gợi ý 2", "gợi ý 3"]
}
"""

    user_content = (
        f"Mode: {mode}\n"
        "Mode guidance: Với Thống kê dataset, trả lời trực tiếp bằng số liệu từ Dataset context, không sinh code. Với Sinh chart/code hoặc Sửa code mới sinh code.\n"
        f"Dataset context:\n{dataset_context}\n\n"
        f"Extra context:\n{extra_context}\n\n"
        f"Code nguoi dung/AI dang co:\n{code_input}\n\n"
        f"Yeu cau nguoi dung:\n{prompt}\n"
    )

    messages = [
        {"role": "system", "content": BASE_SYSTEM_PROMPT + json_instruction},
        {"role": "user", "content": user_content},
    ]

    def call_groq(attempt: ModelAttempt):
        client = Groq(api_key=attempt.api_key)
        max_tokens = 3000 if attempt.model == primary_model else 2500
        return client.chat.completions.create(
            model=attempt.model,
            messages=messages,
            temperature=0.15,
            max_tokens=max_tokens,
        )

    try:
        response = execute_model_attempts(
            "Groq",
            attempts,
            call_groq,
        )
    except ModelAttemptsExhaustedError:
        return AIResponse(
            answer=(
                "Đã thử tất cả cấu hình key/model Groq nhưng provider "
                "hiện không khả dụng. Vui lòng thử lại sau."
            )
        )
    except Exception:
        return AIResponse(
            answer=(
                "Không thể xử lý yêu cầu Groq do lỗi không thể fallback. "
                "Vui lòng kiểm tra đầu vào và thử lại."
            )
        )

    text = response.choices[0].message.content or ""
    data = _extract_json(text)

    if not data:
        cleaned_text = _strip_thinking(text)
        code = _extract_python_code(cleaned_text)
        answer_match = re.search(r'"answer"\s*:\s*"(.*?)"\s*,\s*"code"', cleaned_text, re.DOTALL)
        answer = answer_match.group(1).strip() if answer_match else cleaned_text
        return AIResponse(answer=answer, code=code)

    return AIResponse(
        answer=str(data.get("answer", "")),
        code=str(data.get("code", "")),
        chart_title=str(data.get("chart_title", "")),
        suggestions=data.get("suggestions") if isinstance(data.get("suggestions"), list) else [],
    )


def ask_gemini_vision(config: AIConfig, image_bytes: bytes, filename: str, prompt: str) -> str:
    attempts = build_model_attempts("gemini", config)
    if not attempts:
        return (
            "Thiếu GEMINI_API_KEY hoặc GEMINI_API_KEY_BACKUP trong file .env "
            "nên chưa thể phân tích ảnh bằng Gemini Vision."
        )

    from google import genai
    from google.genai import types

    mime_type = mimetypes.guess_type(filename)[0] or "image/png"
    vision_prompt = f"""
Bạn là chuyên gia phân tích dashboard/biểu đồ khí hậu.
Phân tích ảnh người dùng cung cấp theo yêu cầu sau:
{prompt}

Quy tắc:
- Chỉ mô tả/kết luận từ nội dung nhìn thấy trong ảnh.
- Không bịa số liệu không nhìn thấy rõ.
- Trả lời bằng tiếng Việt.
"""

    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        vision_prompt,
    ]

    def call_gemini(attempt: ModelAttempt):
        client = genai.Client(api_key=attempt.api_key)
        return client.models.generate_content(
            model=attempt.model,
            contents=contents,
        )

    try:
        response = execute_model_attempts(
            "Gemini",
            attempts,
            call_gemini,
        )
    except ModelAttemptsExhaustedError:
        return (
            "Đã thử tất cả cấu hình key/model Gemini nhưng provider "
            "hiện không khả dụng. Vui lòng thử lại sau."
        )
    except Exception:
        return (
            "Không thể xử lý yêu cầu Gemini do lỗi không thể fallback. "
            "Vui lòng kiểm tra đầu vào và thử lại."
        )
    return response.text or ""
