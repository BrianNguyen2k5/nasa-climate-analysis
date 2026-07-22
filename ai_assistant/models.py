from __future__ import annotations

import json
import mimetypes
import re
from dataclasses import dataclass

from .config import AIConfig


@dataclass
class AIResponse:
    answer: str
    code: str = ""
    suggestions: list[str] | None = None
    chart_title: str = ""


BASE_SYSTEM_PROMPT = """
Bạn là trợ lý AI phân tích dữ liệu khí hậu tích hợp trong dashboard Streamlit.
Quy tắc bắt buộc:
- Trả lời bằng tiếng Việt, rõ ràng, có số liệu nếu số liệu đến từ dataset/ngữ cảnh được cung cấp.
- Không bịa dữ liệu, không bịa hình ảnh, không tạo dataset giả.
- Không tiết lộ, không mô tả, không sinh lại code dashboard/group/project. Chỉ được sinh code phân tích ngắn chạy trên DataFrame `df` khi người dùng yêu cầu.
- Nếu sinh code, code phải dùng DataFrame `df` đã có sẵn và các biến đã được nạp sẵn: `pd`, `np`, `px`, `go`. Tuyệt đối không viết import. Code phải tạo biến `fig`. Khi lọc thành phố, dùng `location_name` với các giá trị đúng trong dataset như `Buon Ma Thuot`, `Ho Chi Minh City`, `Ha Noi`, `Da Nang`.
- Code phải có comment tiếng Việt giải thích thao tác chính.
- Không dùng import/from import, open, os, sys, subprocess, network request, đọc/ghi file, eval, exec. Không viết `import plotly.express as px` hoặc `import plotly.graph_objects as go` vì `px` và `go` đã có sẵn.
- Code sinh ra ở trạng thái chờ duyệt; con người có quyền sửa trước khi thực thi.
"""


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
    if not config.groq_api_key:
        return AIResponse(
            answer="Thiếu GROQ_API_KEY trong file .env nên chưa thể gọi Groq.",
            suggestions=[
                "Thêm GROQ_API_KEY vào .env",
                "Chạy lại Streamlit sau khi cập nhật biến môi trường",
            ],
        )

    from groq import Groq

    client = Groq(api_key=config.groq_api_key)
    wants_code = mode in {"Sinh chart/code", "Sửa code"}
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

    model = config.groq_code_model if wants_code else config.groq_primary_model
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT + json_instruction},
                {"role": "user", "content": user_content},
            ],
            temperature=0.15,
            max_tokens=3000,
        )
    except Exception as primary_error:
        try:
            response = client.chat.completions.create(
                model=config.groq_backup_model,
                messages=[
                    {"role": "system", "content": BASE_SYSTEM_PROMPT + json_instruction},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.15,
                max_tokens=2500,
            )
        except Exception as backup_error:
            return AIResponse(
                answer=(
                    "Không thể gọi Groq API. "
                    f"Lỗi model chính: {primary_error}. "
                    f"Lỗi model dự phòng: {backup_error}."
                )
            )

    text = response.choices[0].message.content or ""
    data = _extract_json(text)

    if not data and wants_code and model != config.groq_primary_model:
        try:
            response = client.chat.completions.create(
                model=config.groq_primary_model,
                messages=[
                    {"role": "system", "content": BASE_SYSTEM_PROMPT + json_instruction},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                max_tokens=2500,
            )
            text = response.choices[0].message.content or ""
            data = _extract_json(text)
        except Exception:
            pass

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
    if not config.gemini_api_key:
        return "Thiếu GEMINI_API_KEY trong file .env nên chưa thể phân tích ảnh bằng Gemini Vision."

    from google import genai
    from google.genai import types

    mime_type = mimetypes.guess_type(filename)[0] or "image/png"
    client = genai.Client(api_key=config.gemini_api_key)
    vision_prompt = f"""
Bạn là chuyên gia phân tích dashboard/biểu đồ khí hậu.
Phân tích ảnh người dùng cung cấp theo yêu cầu sau:
{prompt}

Quy tắc:
- Chỉ mô tả/kết luận từ nội dung nhìn thấy trong ảnh.
- Không bịa số liệu không nhìn thấy rõ.
- Trả lời bằng tiếng Việt.
"""
    try:
        response = client.models.generate_content(
            model=config.gemini_primary_model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                vision_prompt,
            ],
        )
    except Exception:
        response = client.models.generate_content(
            model=config.gemini_backup_model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                vision_prompt,
            ],
        )
    return response.text or ""

