import json
import requests
import streamlit as st
import plotly.io as pio

API_BASE = "http://localhost:8000/api"


def render_ai_assistant_tab(placeholder_box=None) -> None:
    tab_studio, tab_logs = st.tabs(["AI Studio & Phê Duyệt Code", "Nhật Ký Thực Thi (API Logs)"])

    # ---------------------------------------------------------
    # TAB 1: AI STUDIO & HUMAN-IN-THE-LOOP EXECUTION
    # ---------------------------------------------------------
    with tab_studio:
        # Input Prompt from User
        chat_prompt = st.chat_input("Nhập yêu cầu phân tích khí hậu hoặc viết code Python...")
        active_prompt = chat_prompt

        # Call AI Generate Endpoint if prompt entered
        if active_prompt:
            st.session_state.ai_prompt = active_prompt
            with st.spinner("AI đang phân tích metadata và khởi tạo mã nguồn..."):
                try:
                    res = requests.post(f"{API_BASE}/ai/generate", json={"prompt": active_prompt}, timeout=60)
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.ai_code = data.get("code", "")
                        st.session_state.ai_explanation = data.get("explanation", "")
                        st.session_state.exec_result = None  # Reset previous run result
                    else:
                        st.error(f"Lỗi API Sinh Code ({res.status_code}): {res.text}")
                except Exception as e:
                    st.error(f"Không thể kết nối đến Backend API ({API_BASE}). Vui lòng đảm bảo server FastAPI đang chạy tại port 8000. Chi tiết: {e}")

        # Render Human-in-the-Loop Code Review Area
        if "ai_code" in st.session_state and st.session_state.ai_code:
            st.markdown("---")
            st.markdown("#### 1. Đề xuất & Giải thích từ AI")
            st.info(st.session_state.get("ai_explanation", "AI đã tạo thành công câu lệnh phân tích."))

            st.markdown("#### 2. Phê duyệt & Chỉnh sửa Mã Nguồn Local")

            # Editable code box
            edited_code = st.text_area(
                "Mã Python thực thi (Plotly / Pandas):",
                value=st.session_state.ai_code,
                height=500,
                key="code_editor_area",
            )

            # Approval Action Button
            btn_col1, btn_col2 = st.columns([1, 3])
            with btn_col1:
                run_approved = st.button("Chấp Nhận & Thực Thi", type="primary", use_container_width=True)

            if run_approved:
                with st.spinner("Đang thực thi mã Python trên dữ liệu local..."):
                    try:
                        payload = {
                            "prompt": st.session_state.get("ai_prompt", "Yêu cầu tùy chỉnh"),
                            "original_code": st.session_state.ai_code,
                            "approved_code": edited_code,
                        }
                        res = requests.post(f"{API_BASE}/execute", json=payload, timeout=60)
                        if res.status_code == 200:
                            st.session_state.exec_result = res.json()
                            st.success("Thực thi mã nguồn thành công! Biểu đồ tương tác đã được khởi tạo.")
                        else:
                            st.session_state.exec_result = None
                            st.error(f"Lỗi khi thực thi mã Python ({res.status_code}): {res.json().get('detail')}")
                    except Exception as e:
                        st.error(f"Không thể kết nối Backend API thực thi: {e}")

        # Display Execution Output (Plotly Figure)
        if "exec_result" in st.session_state and st.session_state.exec_result:
            exec_res = st.session_state.exec_result
            st.markdown("---")
            st.markdown("#### 3. Kết quả Phân tích Trực quan")

            fig_json = exec_res.get("fig_json")
            if fig_json:
                try:
                    fig = pio.from_json(json.dumps(fig_json))
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as err:
                    st.warning(f"Không thể hiển thị đối tượng Plotly Figure: {err}")

    # ---------------------------------------------------------
    # TAB 2: API LOGS VIEWER (MỤC 2.2 & 5.2 BẮT BUỘC)
    # ---------------------------------------------------------
    with tab_logs:
        st.markdown("##### Nhật ký lưu trữ yêu cầu, mã nguồn & kết quả (API Logs)")
        st.caption("Đáp ứng quy định lưu trữ truy xuất lại lịch sử phân tích của bài tập.")

        top_col1, top_col2 = st.columns([1, 4])
        with top_col1:
            refresh_logs = st.button("Tải lại Nhật ký", use_container_width=True)

        try:
            res = requests.get(f"{API_BASE}/logs", timeout=5)
            if res.status_code == 200:
                logs_data = res.json().get("logs", [])

                if not logs_data:
                    st.info("Chưa có lịch sử thực thi nào được ghi lại.")
                else:
                    st.markdown("###### Danh sách bản ghi chi tiết:")

                    for idx, log in enumerate(logs_data):
                        status_badge = "SUCCESS" if log.get("status") == "SUCCESS" else "FAILED"
                        timestamp = log.get("timestamp", "N/A")
                        prompt = log.get("prompt", "Không có prompt")

                        with st.expander(f"[{timestamp}] {status_badge} - Prompt: {prompt[:60]}..."):
                            st.markdown(f"**Thời gian:** `{timestamp}`")
                            st.markdown(f"**Yêu cầu ban đầu:** {prompt}")

                            st.markdown("**Mã Python đã được con người duyệt & chạy:**")
                            st.code(log.get("approved_code", "# Empty"), language="python")

                            if log.get("error_message"):
                                st.error(f"Thông báo lỗi: {log.get('error_message')}")
            else:
                st.error("Không thể lấy dữ liệu logs từ Backend API.")
        except Exception as e:
            st.info(f"Chưa thể kết nối Backend API để tải logs. Vui lòng đảm bảo FastAPI backend đang chạy (`uvicorn api.main:app --port 8000`). Chi tiết: {e}")
