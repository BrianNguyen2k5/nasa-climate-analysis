import streamlit as st


def render_temperature_comparison_tab(placeholder_box) -> None:
    st.markdown('<div class="section-title">So sánh nhiệt độ</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="small-note">Khu vực dành cho nhiệt độ trung bình, cực trị nhiệt và xu thế nóng lên theo vùng.</p>',
        unsafe_allow_html=True,
    )

    top_left, top_right = st.columns([1.2, 1])
    with top_left:
        placeholder_box(
            "Chuỗi thời gian nhiệt độ trung bình",
            "Biểu đồ sẽ được bổ sung: diễn biến nhiệt độ theo năm hoặc tháng cho các vùng được chọn.",
            kicker="Nhiệt độ",
            tall=True,
        )
    with top_right:
        placeholder_box(
            "So sánh nhiệt độ theo điểm tham chiếu",
            "Biểu đồ sẽ được bổ sung: bảng hoặc heatmap so sánh 20 địa điểm.",
            kicker="Điểm tham chiếu",
        )
        st.write("")
        placeholder_box(
            "Chênh lệch nhiệt độ vùng",
            "Biểu đồ sẽ được bổ sung: độ lệch so với trung bình toàn quốc hoặc mốc nền.",
            kicker="Dị thường",
        )

    cols = st.columns(3)
    with cols[0]:
        placeholder_box("Nhiệt độ tối cao", "Biểu đồ sẽ được bổ sung.", kicker="Tx")
    with cols[1]:
        placeholder_box("Nhiệt độ tối thấp", "Biểu đồ sẽ được bổ sung.", kicker="Tn")
    with cols[2]:
        placeholder_box("Biên độ nhiệt", "Biểu đồ sẽ được bổ sung.", kicker="Dao động")
