import json
import uuid

import plotly.io as pio
import streamlit as st

from ai_assistant.code_runner import execute_chart_code
from ai_assistant.chart_summary import summarize_chart
from ai_assistant.chart_templates import build_chart_code_from_prompt
from ai_assistant.code_edit_templates import apply_simple_code_edit
from ai_assistant.code_sanitizer import (
    sanitize_generated_code,
    validate_ai_edit_for_application,
    validate_runner_compatibility,
)
from ai_assistant.config import load_ai_config
from ai_assistant.conversation_state import (
    FAILED,
    PENDING_APPROVAL,
    PROMPT_WIDGET_KEY,
    SUCCESS,
    apply_ai_edit_response,
    apply_pending_prompt_reset,
    attach_chart_conclusion,
    attach_execution_result,
    code_sha256,
    create_code_proposal_message,
    find_message_by_id,
    is_code_proposal,
    latest_code_proposal_id,
    mark_proposal_approved,
    normalize_messages,
    proposal_ui_policy,
    request_prompt_reset_on_rerun,
    reset_ai_transient_state,
    resolve_ai_edit_source,
    update_proposal_code,
)
from ai_assistant.data_context import dataset_context, load_dataset
from ai_assistant.dataset_qa import answer_dataset_question
from ai_assistant.logs import (
    append_message,
    create_session,
    load_sessions,
    save_session_messages,
)
from ai_assistant.models import (
    INVALID_CODE_RESPONSE_MESSAGE,
    ask_gemini_vision,
    ask_groq,
    sanitize_ai_response,
    sanitize_model_text,
)


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


def _persist_active_messages() -> None:
    save_session_messages(
        st.session_state.ai_session_id,
        st.session_state.ai_messages,
    )


def _append_message_object(message: dict) -> dict:
    st.session_state.ai_messages.append(message)
    metadata = {
        key: value
        for key, value in message.items()
        if key not in {"role", "content"}
    }
    append_message(
        st.session_state.ai_session_id,
        str(message.get("role", "assistant")),
        str(message.get("content", "")),
        **metadata,
    )
    return message


def _add_message(role: str, content: str, **metadata) -> dict:
    message = {
        "id": str(uuid.uuid4()),
        "role": role,
        "kind": "text",
        "content": content,
        **metadata,
    }
    return _append_message_object(message)


def _append_code_proposal(answer: str, code: str, **metadata) -> dict:
    proposal = create_code_proposal_message(answer, code, **metadata)
    _append_message_object(proposal)
    st.session_state.active_proposal_message_id = proposal["id"]
    return proposal


def _load_session_into_state(session: dict) -> None:
    reset_ai_transient_state(st.session_state)
    st.session_state.ai_session_id = session["id"]
    st.session_state.ai_messages = normalize_messages(session.get("messages", []))
    active_id = latest_code_proposal_id(st.session_state.ai_messages)
    if active_id:
        st.session_state.active_proposal_message_id = active_id


def _ensure_state() -> None:
    apply_pending_prompt_reset(st.session_state)
    requested_session_id = st.session_state.pop("ai_requested_session_id", None)
    if requested_session_id:
        requested_session = next(
            (
                session
                for session in load_sessions()
                if session.get("id") == requested_session_id
            ),
            None,
        )
        if requested_session is not None:
            _load_session_into_state(requested_session)

    if "ai_session_id" not in st.session_state:
        session = create_session("Hoi thoai AI khi hau")
        st.session_state.ai_session_id = session["id"]
        st.session_state.ai_messages = []
    elif "ai_messages" not in st.session_state:
        session = next(
            (
                item
                for item in load_sessions()
                if item.get("id") == st.session_state.ai_session_id
            ),
            None,
        )
        st.session_state.ai_messages = session.get("messages", []) if session else []

    st.session_state.ai_messages = normalize_messages(st.session_state.ai_messages)

    legacy_pending_code = st.session_state.pop("ai_pending_code", "")
    legacy_pending_answer = st.session_state.pop("ai_pending_answer", "")
    st.session_state.pop("ai_last_result", None)
    st.session_state.pop("ai_chart_conclusion", None)
    st.session_state.pop("ai_code_editor", None)
    st.session_state.pop("ai_fix_instruction", None)
    if legacy_pending_code and not latest_code_proposal_id(st.session_state.ai_messages):
        _append_code_proposal(
            str(legacy_pending_answer or "Code được chuyển từ phiên làm việc trước."),
            str(legacy_pending_code),
            source="legacy_state_migration",
        )

    active_id = st.session_state.get("active_proposal_message_id")
    active_message = (
        find_message_by_id(st.session_state.ai_messages, str(active_id))
        if active_id
        else None
    )
    if active_message is None or not is_code_proposal(active_message):
        latest_id = latest_code_proposal_id(st.session_state.ai_messages)
        if latest_id:
            st.session_state.active_proposal_message_id = latest_id


def _new_chat() -> None:
    reset_ai_transient_state(st.session_state)
    session = create_session("Hoi thoai AI khi hau")
    st.session_state.ai_session_id = session["id"]
    st.session_state.ai_messages = []


def _request_open_chat(session_id: str) -> None:
    st.session_state.ai_requested_session_id = session_id
    st.rerun()


def _render_ai_response_detail(message: dict, label: str = "Xem câu trả lời") -> None:
    with st.expander(label, expanded=False):
        st.markdown(message.get("content", ""))
        if message.get("status"):
            st.caption(f"Trạng thái: {message['status']}")


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


def _render_proposal_result(message: dict, config, context_text: str) -> None:
    result = message.get("result")
    if message.get("status") == SUCCESS:
        success_message = (
            result.get("message")
            if isinstance(result, dict) and result.get("message")
            else "Thực thi thành công trên dữ liệu local."
        )
        st.success(str(success_message))

    error = message.get("error")
    if error:
        st.error(str(error))

    if not isinstance(result, dict) or not result.get("fig_json"):
        conclusion = message.get("conclusion")
        if conclusion:
            st.markdown("#### Kết luận từ AI")
            st.info(str(conclusion))
        return

    st.markdown("#### Kết quả trực quan")
    fig = pio.from_json(json.dumps(result["fig_json"]))
    st.plotly_chart(fig, use_container_width=True)
    if result.get("table_preview"):
        st.markdown("#### Bảng dữ liệu trung gian")
        st.dataframe(result["table_preview"], use_container_width=True)

    message_id = str(message["id"])
    if st.button(
        "AI kết luận biểu đồ vừa tạo",
        key=f"ai_conclude_chart_{message_id}",
        use_container_width=True,
    ):
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
        attach_chart_conclusion(
            st.session_state.ai_messages,
            message_id,
            conclusion,
            response.suggestions,
        )
        _persist_active_messages()

    conclusion = message.get("conclusion")
    if conclusion:
        st.markdown("#### Kết luận từ AI")
        st.info(str(conclusion))


def _render_code_review(message_id: str, df, config, context_text: str) -> None:
    message = find_message_by_id(st.session_state.ai_messages, message_id)
    if message is None or not is_code_proposal(message):
        return

    revision = int(message.get("revision") or 1)
    editor_key = f"ai_code_editor_{message_id}_{revision}"
    fix_key = f"ai_fix_instruction_{message_id}_{revision}"

    st.markdown("#### Code đang chờ duyệt")
    st.caption("Bạn có thể sửa trực tiếp trước khi chạy. Code chỉ chạy khi bấm nút phê duyệt.")
    edited_code = st.text_area(
        "Mã Python phân tích local",
        value=str(message.get("current_code", "")),
        height=360,
        key=editor_key,
    )

    fix_instruction = st.text_input(
        "Bạn muốn AI sửa gì trong code này?",
        placeholder="Ví dụ: bỏ import, sửa tên địa điểm, đổi sang biểu đồ đường, thêm nhãn số liệu...",
        key=fix_key,
    )

    col_run, col_fix, col_clear = st.columns([1.1, 1.1, 3])
    with col_run:
        run_code = st.button(
            "Chấp nhận & chạy",
            key=f"ai_run_code_{message_id}_{revision}",
            type="primary",
            use_container_width=True,
        )
    with col_fix:
        ask_fix = st.button(
            "Nhờ AI sửa code",
            key=f"ai_request_fix_{message_id}_{revision}",
            use_container_width=True,
        )
    with col_clear:
        st.caption("Môi trường chạy có sẵn: `df`, `pd`, `np`, `px`, `go`.")

    if (
        edited_code != message.get("current_code", "")
        and not ask_fix
        and not run_code
    ):
        message = update_proposal_code(
            st.session_state.ai_messages,
            message_id,
            edited_code,
        )
        _persist_active_messages()

    if ask_fix:
        source_code = resolve_ai_edit_source(message, edited_code)
        user_fix = fix_instruction.strip() or "Sửa code để chạy được an toàn, vẫn tạo biến `fig`, không dùng import/file/network."
        fix_prompt = (
            f"{user_fix}\n\n"
            "Trả lại toàn bộ chương trình Python sau khi sửa, không trả diff, "
            "fragment hoặc placeholder. Chỉ sửa đúng nội dung được yêu cầu và "
            "giữ nguyên mọi logic, filter, metric, aggregation, chart type, "
            "x/y/color/labels/title không liên quan. Đây là code cho local "
            "runner; app tự lấy và render biến `fig`. Không dùng "
            "import/file/network, không tự tạo dữ liệu giả và tuyệt đối không "
            "gọi print/display/show/st/plt hoặc renderer khác."
        )
        with st.spinner("Groq đang sửa code..."):
            response = ask_groq(
                config,
                fix_prompt,
                context_text,
                "Sửa code",
                code_input=source_code,
            )
        if not response.code.strip():
            st.warning(INVALID_CODE_RESPONSE_MESSAGE)
            return
        fixed_code = sanitize_generated_code(
            response.code,
            preserve_imports=True,
        )
        if fixed_code:
            fixed_code = sanitize_generated_code(
                apply_simple_code_edit(fixed_code, user_fix),
                preserve_imports=True,
            )
        validation = validate_ai_edit_for_application(
            source_code,
            fixed_code,
            user_fix,
        )
        if not validation.valid:
            st.warning(validation.message)
            return
        fixed_answer = response.answer or (
            "Đã sửa code theo yêu cầu. Bạn có thể kiểm tra lại trước khi chạy."
        )
        _, edit_applied = apply_ai_edit_response(
            st.session_state.ai_messages,
            message_id,
            fixed_code,
            edit_instruction=user_fix,
            edit_answer=fixed_answer,
            source_code=source_code,
        )
        if not edit_applied:
            st.warning(
                "AI chưa trả về mã Python để cập nhật. "
                "Nội dung trong editor được giữ nguyên."
            )
            return
        _persist_active_messages()
        st.rerun()

    if run_code:
        approved_code = edited_code
        runner_validation = validate_runner_compatibility(approved_code)
        if not runner_validation.valid:
            st.warning(runner_validation.message)
            return

        approved_message = mark_proposal_approved(
            st.session_state.ai_messages,
            message_id,
            approved_code,
        )
        _persist_active_messages()
        code_to_execute = str(approved_message["current_code"])
        if code_sha256(approved_code) != code_sha256(code_to_execute):
            raise RuntimeError("Code được duyệt không khớp code chuẩn bị thực thi.")

        with st.spinner("Đang chạy code đã duyệt trên dữ liệu local..."):
            result = execute_chart_code(code_to_execute, df)

        result_dict = result.__dict__
        attach_execution_result(
            st.session_state.ai_messages,
            message_id,
            executed_code=code_to_execute,
            ok=result.ok,
            result=result_dict if result.ok else None,
            error=None if result.ok else result.message,
            chart_metadata={"result_context": _result_context(result_dict)} if result.ok else None,
        )
        _persist_active_messages()
        st.rerun()


def _render_code_proposal(
    message: dict,
    proposal_number: int,
    latest_success_id: str | None,
    df,
    config,
    context_text: str,
) -> None:
    message_id = str(message["id"])
    status = str(message.get("status") or PENDING_APPROVAL)
    policy = proposal_ui_policy(status)
    expanded = bool(policy["expanded"])
    if status == SUCCESS and message_id == latest_success_id:
        expanded = True
    label = f"{policy['label_prefix']} #{proposal_number} · {status}"

    with st.expander(label, expanded=expanded):
        st.markdown(str(message.get("answer") or message.get("content") or ""))
        st.caption(f"Trạng thái: {status}")

        edit_history = message.get("edit_history") or []
        if (
            policy["show_edit_explanation"]
            and edit_history
            and edit_history[-1].get("answer")
        ):
            st.info(str(edit_history[-1]["answer"]))

        if status == SUCCESS:
            _render_proposal_result(message, config, context_text)
            st.markdown("#### Code đã thực thi")
            st.code(
                str(message.get("executed_code") or message.get("current_code") or ""),
                language="python",
            )
        elif status == FAILED:
            _render_proposal_result(message, config, context_text)
            _render_code_review(message_id, df, config, context_text)
        elif policy["show_editor"]:
            _render_code_review(message_id, df, config, context_text)
        else:
            st.code(
                str(message.get("current_code") or message.get("code") or ""),
                language="python",
            )


def _render_messages(df, config, context_text: str) -> None:
    latest_success_id = next(
        (
            str(message["id"])
            for message in reversed(st.session_state.ai_messages)
            if is_code_proposal(message) and message.get("status") == SUCCESS
        ),
        None,
    )
    answer_index = 1
    for message in st.session_state.ai_messages:
        role = message.get("role")
        if role == "user":
            with st.chat_message("user"):
                st.markdown(message.get("content", ""))
            continue

        with st.chat_message("assistant"):
            if is_code_proposal(message):
                _render_code_proposal(
                    message,
                    answer_index,
                    latest_success_id,
                    df,
                    config,
                    context_text,
                )
            else:
                _render_ai_response_detail(message, f"Xem câu trả lời AI #{answer_index}")
            answer_index += 1


def _render_history() -> None:
    sessions = [session for session in load_sessions() if session.get("messages")]
    if not sessions:
        st.info("Chưa có hội thoại AI nào.")
        return

    for session in sessions:
        label = f"{session.get('updated_at', '')} - {session.get('title', 'Hoi thoai AI')}"
        with st.expander(label):
            if st.button(
                "Mở hội thoại",
                key=f"ai_open_chat_{session.get('id')}",
                use_container_width=True,
            ):
                _request_open_chat(str(session["id"]))
            answer_index = 1
            for message in normalize_messages(session.get("messages", [])):
                if message.get("role") == "user":
                    st.markdown(f"**Người dùng:** {message.get('content', '')}")
                elif is_code_proposal(message):
                    st.markdown(f"**AI:** {message.get('answer', message.get('content', ''))}")
                    st.code(message.get("current_code", ""), language="python")
                    st.caption(f"Trạng thái: {message.get('status', PENDING_APPROVAL)}")
                    if message.get("error"):
                        st.error(str(message["error"]))
                    if message.get("conclusion"):
                        st.info(str(message["conclusion"]))
                    answer_index += 1
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
            value=st.session_state.get(PROMPT_WIDGET_KEY, ""),
            height=120,
            placeholder=PROMPT_PLACEHOLDERS.get(mode, "Nhập yêu cầu phân tích khí hậu..."),
            key=PROMPT_WIDGET_KEY,
        )

        send = st.button(
            "Gửi yêu cầu cho AI",
            type="primary",
            use_container_width=True,
        )

        _render_messages(df, config, context_text)

        if send and prompt.strip():
            request_id = str(uuid.uuid4())
            _add_message("user", prompt, mode=mode, request_id=request_id)

            if mode == "Thống kê dataset":
                local_answer = answer_dataset_question(prompt, df)
                if local_answer:
                    _add_message(
                        "assistant",
                        local_answer,
                        source="local_dataset_query",
                        request_id=request_id,
                    )
                    request_prompt_reset_on_rerun(st.session_state)
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
                vision_text = sanitize_model_text(vision_text)
                if not vision_text:
                    vision_text = (
                        "Phản hồi Gemini không chứa nội dung an toàn để hiển thị. "
                        "Vui lòng thử lại."
                    )
                if mode == "Kết luận chart/dataset":
                    _add_message(
                        "assistant",
                        vision_text,
                        mode="Gemini Vision",
                        source="gemini_vision",
                        request_id=request_id,
                    )
                    request_prompt_reset_on_rerun(st.session_state)
                    st.rerun()

                extra_context = f"Ket qua Gemini Vision tu anh:\n{vision_text}"

            active_id = st.session_state.get("active_proposal_message_id")
            active_message = (
                find_message_by_id(st.session_state.ai_messages, str(active_id))
                if active_id
                else None
            )
            active_code = (
                str(active_message.get("current_code", ""))
                if active_message is not None and is_code_proposal(active_message)
                else ""
            )

            with st.spinner("Groq đang xử lý yêu cầu..."):
                response = ask_groq(
                    config,
                    prompt,
                    context_text,
                    mode,
                    extra_context=extra_context,
                    code_input=active_code,
                )
            response = sanitize_ai_response(response)

            response_source = "groq"
            if mode == "Sinh chart/code" and not response.code:
                fallback = build_chart_code_from_prompt(prompt, df)
                if fallback:
                    fallback_answer, fallback_code = fallback
                    response.answer = fallback_answer
                    response.code = fallback_code
                    response_source = "local_chart_template"

            if response.code:
                sanitized_code = sanitize_generated_code(response.code)
                if sanitized_code:
                    _append_code_proposal(
                        response.answer or "Code đã được tạo và đang chờ bạn duyệt.",
                        sanitized_code,
                        suggestions=response.suggestions,
                        chart_title=response.chart_title,
                        request_id=request_id,
                        source=response_source,
                    )
                else:
                    _add_message(
                        "assistant",
                        response.answer or "Code sinh ra không vượt qua kiểm tra an toàn.",
                        suggestions=response.suggestions,
                        chart_title=response.chart_title,
                        request_id=request_id,
                        source=response_source,
                    )
            else:
                _add_message(
                    "assistant",
                    response.answer,
                    suggestions=response.suggestions,
                    chart_title=response.chart_title,
                    request_id=request_id,
                    source=response_source,
                )
            request_prompt_reset_on_rerun(st.session_state)
            st.rerun()

    with tab_logs:
        st.markdown("### Lịch sử hội thoại")
        st.caption(
            "Log lưu theo từng đoạn chat, gồm prompt, phản hồi, code, trạng thái chạy và kết quả tóm tắt.")
        _render_history()
