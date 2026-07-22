import json
import uuid

import plotly.io as pio
import streamlit as st

from ai_assistant.code_runner import execute_chart_code
from ai_assistant.chart_summary import summarize_chart
from ai_assistant.chart_templates import build_chart_code_from_prompt
from ai_assistant.code_edit_templates import apply_simple_code_edit
from ai_assistant.code_sanitizer import sanitize_generated_code
from ai_assistant.config import load_ai_config
from ai_assistant.data_context import dataset_context, load_dataset
from ai_assistant.dataset_qa import answer_dataset_question
from ai_assistant.logs import append_message, create_session, load_sessions
from ai_assistant.models import ask_gemini_vision, ask_groq


@st.cache_data(show_spinner=False)
def _load_ai_data_and_context():
    context_version = 2
    df = load_dataset()
    return df, dataset_context(df), context_version

TASKS = [
    "AI gợi ý",
    "Sinh chart/code",
    "Kết luận chart/dataset",
    "Thống kê dataset",
]


PROMPT_PLACEHOLDERS = {
    "AI gợi ý": "Ví dụ: Gợi ý 5 hướng phân tích khí hậu đáng làm với dataset NASA Việt Nam này.",
    "Sinh chart/code": "Ví dụ: Vẽ biểu đồ nhiệt độ trung bình năm 2015 tại Buôn Ma Thuột và TP Hồ Chí Minh.",
    "Kết luận chart/dataset": "Ví dụ: Nhận xét xu hướng nhiệt độ và lượng mưa giữa các vùng trong dataset.",
    "Thống kê dataset": "Ví dụ: Nhiệt độ trung bình của Buôn Ma Thuột năm 2025 là bao nhiêu?",
}




def _ensure_state() -> None:
    if "ai_session_id" not in st.session_state:
        session = create_session("Hoi thoai AI khi hau")
        st.session_state.ai_session_id = session["id"]
        st.session_state.ai_messages = []
    if "ai_messages" not in st.session_state:
        sessions = load_sessions()
        session = next(
            (item for item in sessions if item["id"]
             == st.session_state.ai_session_id),
            None,
        )
        st.session_state.ai_messages = session.get(
            "messages", []) if session else []

def _new_chat() -> None:
    session = create_session("Hoi thoai AI khi hau")
    st.session_state.ai_session_id = session["id"]
    st.session_state.ai_messages = []
    st.session_state.pop("ai_pending_code", None)
    st.session_state.pop("ai_pending_answer", None)
    st.session_state.pop("ai_last_result", None)

def _add_message(role: str, content: str, **metadata) -> None:
    st.session_state.ai_messages.append(
        {"role": role, "content": content, **metadata})
    append_message(st.session_state.ai_session_id, role, content, **metadata)


def _render_ai_response_detail(message: dict, label: str = "Xem câu trả lời") -> None:
    with st.expander(label, expanded=False):
        st.markdown(message.get("content", ""))
        if message.get("code"):
            st.code(message["code"], language="python")
        if message.get("status"):
            st.caption(f"Trạng thái: {message['status']}")


def _message_matches_active_code(message: dict) -> bool:
    pending_code = st.session_state.get("ai_pending_code", "")
    message_code = message.get("code", "")
    if not pending_code or not message_code or message.get("status"):
        return False
    return sanitize_generated_code(message_code).strip() == pending_code.strip()


def _render_messages(df, config, context_text: str) -> bool:
    answer_index = 1
    rendered_active_code = False
    active_message_index = None
    for idx, message in enumerate(st.session_state.ai_messages):
        if message.get("role") == "assistant" and _message_matches_active_code(message):
            active_message_index = idx

    for idx, message in enumerate(st.session_state.ai_messages):
        role = message.get("role")
        if role == "user":
            with st.chat_message("user"):
                st.markdown(message.get("content", ""))
        else:
            with st.chat_message("assistant"):
                _render_ai_response_detail(message, f"Xem câu trả lời AI #{answer_index}")
                if idx == active_message_index:
                    _render_code_review(df, config, context_text)
                    rendered_active_code = True
                answer_index += 1
    return rendered_active_code
def _result_context(result: dict) -> str:
    fig_json = result.get("fig_json") or {}
    layout = fig_json.get("layout", {})
    traces = fig_json.get("data", [])
    trace_summary = [
        {
            "type": trace.get("type"),
            "name": trace.get("name"),
            "x_sample": trace.get("x", [])[:5] if isinstance(trace.get("x"), list) else None,
            "y_sample": trace.get("y", [])[:5] if isinstance(trace.get("y"), list) else None,
        }
        for trace in traces[:8]
    ]
    return json.dumps(
        {
            "title": layout.get("title", {}).get("text") if isinstance(layout.get("title"), dict) else None,
            "xaxis": layout.get("xaxis", {}).get("title", {}).get("text")
            if isinstance(layout.get("xaxis"), dict)
            else None,
            "yaxis": layout.get("yaxis", {}).get("title", {}).get("text")
            if isinstance(layout.get("yaxis"), dict)
            else None,
            "traces": trace_summary,
            "table_preview": result.get("table_preview"),
        },
        ensure_ascii=False,
    )


def _render_code_review(df, config, context_text: str) -> None:
    pending_code = st.session_state.get("ai_pending_code", "")
    if not pending_code:
        return

    st.markdown("#### Code đang chờ duyệt")
    st.caption(
        "Bạn có thể sửa trực tiếp trước khi chạy. Code chỉ chạy khi bấm nút phê duyệt.")
    edited_code = st.text_area(
        "Mã Python phân tích local",
        value=pending_code,
        height=360,
        key="ai_code_editor",
    )

    fix_instruction = st.text_input(
        "Bạn muốn AI sửa gì trong code này?",
        placeholder="Ví dụ: bỏ import, sửa tên địa điểm, đổi sang biểu đồ đường, thêm nhãn số liệu...",
        key="ai_fix_instruction",
    )

    col_run, col_fix, col_clear = st.columns([1.1, 1.1, 3])
    with col_run:
        run_code = st.button("Chấp nhận & chạy",
                             type="primary", use_container_width=True)
    with col_fix:
        ask_fix = st.button("Nhờ AI sửa code", use_container_width=True)
    with col_clear:
        st.caption("Môi trường chạy có sẵn: `df`, `pd`, `np`, `px`, `go`.")

    if ask_fix:
        user_fix = fix_instruction.strip() or "Sửa code để chạy được an toàn, vẫn tạo biến `fig`, không dùng import/file/network."
        fix_prompt = f"{user_fix}\n\nYêu cầu bắt buộc: code sau khi sửa phải tạo biến `fig`, không dùng import/file/network, không tự tạo dữ liệu giả."
        with st.spinner("Groq đang sửa code..."):
            response = ask_groq(
                config,
                fix_prompt,
                context_text,
                "Sửa code",
                code_input=edited_code,
            )
        fixed_code = sanitize_generated_code(response.code)
        if fixed_code:
            fixed_code = sanitize_generated_code(apply_simple_code_edit(fixed_code, user_fix))
        else:
            fixed_code = sanitize_generated_code(apply_simple_code_edit(edited_code, user_fix))
        fixed_code = fixed_code or sanitize_generated_code(edited_code)

        st.session_state.ai_pending_code = fixed_code
        st.session_state.ai_pending_answer = response.answer or "Đã sửa code theo yêu cầu. Bạn có thể kiểm tra lại trước khi chạy."
        st.session_state.ai_last_result = None
        st.session_state.pop("ai_chart_conclusion", None)
        _add_message("user", user_fix, code=edited_code)
        _add_message("assistant", st.session_state.ai_pending_answer, code=fixed_code, source="code_fix")
        st.rerun()

    if run_code:
        with st.spinner("Đang chạy code đã duyệt trên dữ liệu local..."):
            st.session_state.pop("ai_chart_conclusion", None)
            approved_code = sanitize_generated_code(edited_code)
            result = execute_chart_code(approved_code, df)

        _add_message(
            "assistant",
            result.message,
            code=approved_code,
            status="SUCCESS" if result.ok else "FAILED",
            result=result.__dict__,
        )
        if result.ok:
            st.session_state.ai_last_result = result.__dict__
            st.success(result.message)
        else:
            st.session_state.ai_last_result = None
            st.error(result.message)

    result = st.session_state.get("ai_last_result")
    if result and result.get("fig_json"):
        st.markdown("#### Kết quả trực quan")
        fig = pio.from_json(json.dumps(result["fig_json"]))
        st.plotly_chart(fig, use_container_width=True)
        if result.get("table_preview"):
            with st.expander("Bảng dữ liệu trung gian"):
                st.dataframe(result["table_preview"], use_container_width=True)

        if st.button("AI kết luận biểu đồ vừa tạo", use_container_width=True):
            chart_stats = summarize_chart(result["fig_json"])
            conclusion_prompt = (
                "Hãy viết kết luận phân tích biểu đồ bằng tiếng Việt dựa hoàn toàn trên số liệu tóm tắt bên dưới. "
                "Không tự bịa thêm số liệu. Trình bày ngắn gọn, có nhận xét xu hướng và so sánh chính. "
                "Ở đoạn cuối bắt buộc có tiêu đề `Kết luận chính:` và 1-2 câu tổng hợp ý nghĩa quan trọng nhất của biểu đồ."
            )
            with st.spinner("Groq đang viết kết luận từ số liệu chart..."):
                response = ask_groq(
                    config,
                    conclusion_prompt,
                    context_text,
                    "Kết luận chart/dataset",
                    extra_context=f"Tóm tắt số liệu biểu đồ:\n{chart_stats}",
                )
            conclusion = response.answer or chart_stats
            st.session_state.ai_chart_conclusion = conclusion
            _add_message("user", "AI kết luận biểu đồ vừa tạo")
            _add_message(
                "assistant",
                conclusion,
                suggestions=response.suggestions,
                source="groq_chart_conclusion",
            )

        chart_conclusion = st.session_state.get("ai_chart_conclusion")
        if chart_conclusion:
            st.markdown("#### Kết luận từ AI")
            st.info(chart_conclusion)

def _render_history() -> None:
    sessions = [session for session in load_sessions() if session.get("messages")]
    if not sessions:
        st.info("Chưa có hội thoại AI nào.")
        return

    for session in sessions:
        label = f"{session.get('updated_at', '')} - {session.get('title', 'Hoi thoai AI')}"
        with st.expander(label):
            answer_index = 1
            for message in session.get("messages", []):
                if message.get("role") == "user":
                    st.markdown(f"**Người dùng:** {message.get('content', '')}")
                else:
                    _render_ai_response_detail(message, f"Xem câu trả lời AI #{answer_index}")
                    answer_index += 1

def render_ai_assistant_tab(placeholder_box=None) -> None:
    _ensure_state()
    config = load_ai_config()
    df, context_text, _context_version = _load_ai_data_and_context()

    tab_chat, tab_logs = st.tabs(["AI Workspace", "Lịch sử chat"])

    with tab_chat:
        top_left, top_right = st.columns([2, 1])
        with top_left:
            st.markdown("### Trợ lý AI phân tích khí hậu")
        with top_right:
            if st.button("Chat mới", use_container_width=True):
                _new_chat()
                st.rerun()


        mode = st.segmented_control(
            "Tác vụ",
            TASKS,
            default="AI gợi ý",
            label_visibility="collapsed",
        )

        image_file = st.file_uploader(
            "Input ảnh dashboard/biểu đồ",
            type=["png", "jpg", "jpeg", "webp"],
            help="Gemini Vision phân tích ảnh trước; Groq sẽ chuẩn hóa câu trả lời hoặc sinh code/chart nếu cần.",
        )

        prompt = st.text_area(
            "Yêu cầu của bạn",
            value=st.session_state.get("ai_prompt_box", ""),
            height=120,
            placeholder=PROMPT_PLACEHOLDERS.get(mode, "Nhập yêu cầu phân tích khí hậu..."),
            key="ai_prompt_box",
        )

        send = st.button("Gửi yêu cầu cho AI", type="primary",
                         use_container_width=True)

        rendered_active_code = _render_messages(df, config, context_text)

        if send and prompt.strip():
            request_id = str(uuid.uuid4())
            _add_message("user", prompt, mode=mode, request_id=request_id)

            if mode == "Thống kê dataset":
                local_answer = answer_dataset_question(prompt, df)
                if local_answer:
                    st.session_state.ai_pending_answer = local_answer
                    st.session_state.pop("ai_pending_code", None)
                    st.session_state.pop("ai_last_result", None)
                    _add_message("assistant", local_answer, code="", source="local_dataset_query", request_id=request_id)
                    st.rerun()

            extra_context = ""
            if image_file is not None:
                with st.spinner("Gemini Vision đang phân tích ảnh..."):
                    vision_text = ask_gemini_vision(
                        config,
                        image_file.getvalue(),
                        image_file.name,
                        prompt,
                    )
                extra_context = f"Ket qua Gemini Vision tu anh:\n{vision_text}"
                _add_message("assistant", vision_text,
                             mode="Gemini Vision", request_id=request_id)

            with st.spinner("Groq đang xử lý yêu cầu..."):
                response = ask_groq(
                    config,
                    prompt,
                    context_text,
                    mode,
                    extra_context=extra_context,
                    code_input=st.session_state.get("ai_pending_code", ""),
                )

            if mode == "Sinh chart/code" and not response.code:
                fallback = build_chart_code_from_prompt(prompt, df)
                if fallback:
                    fallback_answer, fallback_code = fallback
                    response.answer = fallback_answer
                    response.code = fallback_code

            st.session_state.ai_pending_answer = response.answer
            if response.code:
                st.session_state.ai_pending_code = sanitize_generated_code(response.code)
                st.session_state.ai_last_result = None
                st.session_state.pop("ai_chart_conclusion", None)

            _add_message(
                "assistant",
                response.answer,
                code=response.code,
                suggestions=response.suggestions,
                chart_title=response.chart_title,
                request_id=request_id,
            )
            st.rerun()

        if not rendered_active_code:
            _render_code_review(df, config, context_text)

    with tab_logs:
        st.markdown("### Lịch sử hội thoại")
        st.caption(
            "Log lưu theo từng đoạn chat, gồm prompt, phản hồi, code, trạng thái chạy và kết quả tóm tắt.")
        _render_history()




