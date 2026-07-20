import streamlit as st


def render_ai_assistant_tab(placeholder_box) -> None:
    st.markdown('<div class="section-title">AI Assistant</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="small-note">Khu vực dự kiến hỗ trợ đặt câu hỏi, tóm tắt phát hiện và gợi ý diễn giải khí hậu khi dữ liệu đã sẵn sàng.</p>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.25, 1])
    with left:
        placeholder_box(
            "Khung hội thoại phân tích khí hậu",
            "Chức năng AI sẽ được bổ sung. Ở giai đoạn này dashboard chưa gọi API, chưa đọc dữ liệu và chưa sinh câu trả lời tự động.",
            kicker="AI",
            tall=True,
        )
    with right:
        placeholder_box(
            "Gợi ý câu hỏi nghiên cứu",
            "Container dành cho các câu hỏi mẫu về xu thế nhiệt độ, mưa, độ ẩm và cực đoan khí hậu.",
            kicker="Prompt",
        )
        st.write("")
        placeholder_box(
            "Tóm tắt phát hiện chính",
            "Container dành cho phần tóm tắt tự động sau khi có dữ liệu và biểu đồ thật.",
            kicker="Summary",
        )

    cols = st.columns(3)
    with cols[0]:
        placeholder_box("Giải thích biểu đồ", "Chức năng sẽ được bổ sung.")
    with cols[1]:
        placeholder_box("Soạn nhận xét học thuật", "Chức năng sẽ được bổ sung.")
    with cols[2]:
        placeholder_box("Kiểm tra bất thường dữ liệu", "Chức năng sẽ được bổ sung.")
