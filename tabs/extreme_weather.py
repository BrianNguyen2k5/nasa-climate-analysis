import streamlit as st


def render_extreme_weather_tab(placeholder_box) -> None:
    st.markdown('<div class="section-title">So sánh thời tiết cực đoan</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="small-note">Khu vực dành cho nắng nóng, mưa lớn, khô hạn và các sự kiện cực đoan theo vùng.</p>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.15, 1])
    with left:
        placeholder_box(
            "Tần suất sự kiện cực đoan",
            "Biểu đồ sẽ được bổ sung: số ngày hoặc số đợt cực đoan theo năm và theo vùng.",
            kicker="Cực đoan",
            tall=True,
        )
    with right:
        placeholder_box(
            "Nắng nóng và rét bất thường",
            "Biểu đồ sẽ được bổ sung: ngưỡng nhiệt độ cực trị và tần suất vượt ngưỡng.",
            kicker="Nhiệt cực trị",
        )
        st.write("")
        placeholder_box(
            "Mưa lớn và khô hạn",
            "Biểu đồ sẽ được bổ sung: mưa cực trị, chuỗi ngày khô và mức tương phản vùng.",
            kicker="Thủy khí hậu",
        )

    cols = st.columns(3)
    with cols[0]:
        placeholder_box("Bản đồ rủi ro", "Biểu đồ sẽ được bổ sung.")
    with cols[1]:
        placeholder_box("Bảng sự kiện nổi bật", "Container dành cho danh sách sự kiện sau khi có dữ liệu.")
    with cols[2]:
        placeholder_box("Tín hiệu xu thế", "Biểu đồ sẽ được bổ sung.")
