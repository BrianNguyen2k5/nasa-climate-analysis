import streamlit as st


def render_rainfall_humidity_tab(placeholder_box) -> None:
    st.markdown('<div class="section-title">So sánh mưa và độ ẩm</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="small-note">Khu vực dành cho lượng mưa, mùa mưa, độ ẩm tương đối và tương phản khô - ẩm.</p>',
        unsafe_allow_html=True,
    )

    rain_col, humidity_col = st.columns(2)
    with rain_col:
        placeholder_box(
            "Tổng lượng mưa theo vùng",
            "Biểu đồ sẽ được bổ sung: so sánh tổng lượng mưa năm hoặc mùa giữa 7 nhóm vùng.",
            kicker="Mưa",
            tall=True,
        )
    with humidity_col:
        placeholder_box(
            "Độ ẩm tương đối theo thời gian",
            "Biểu đồ sẽ được bổ sung: xu thế độ ẩm theo vùng và điểm tham chiếu.",
            kicker="Độ ẩm",
            tall=True,
        )

    cols = st.columns(3)
    with cols[0]:
        placeholder_box("Mùa mưa", "Biểu đồ sẽ được bổ sung.")
    with cols[1]:
        placeholder_box("Số ngày mưa", "Biểu đồ sẽ được bổ sung.")
    with cols[2]:
        placeholder_box("Tương phản khô - ẩm", "Biểu đồ sẽ được bổ sung.")
