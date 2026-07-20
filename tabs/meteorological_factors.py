import streamlit as st


def render_meteorological_factors_tab(placeholder_box) -> None:
    st.markdown('<div class="section-title">So sánh các yếu tố khí tượng</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="small-note">Khu vực dành cho gió, bức xạ, áp suất và các chỉ số phụ trợ khi dữ liệu được nạp.</p>',
        unsafe_allow_html=True,
    )

    main, side = st.columns([1.4, 1])
    with main:
        placeholder_box(
            "Ma trận yếu tố khí tượng theo vùng",
            "Biểu đồ sẽ được bổ sung: so sánh nhiều biến khí tượng giữa 7 nhóm vùng.",
            kicker="Đa biến",
            tall=True,
        )
    with side:
        placeholder_box(
            "Gió và hướng gió",
            "Biểu đồ sẽ được bổ sung: tốc độ gió, hướng gió hoặc phân bố mùa.",
            kicker="Gió",
        )
        st.write("")
        placeholder_box(
            "Bức xạ và cân bằng năng lượng",
            "Biểu đồ sẽ được bổ sung: bức xạ mặt trời và biến thiên theo mùa.",
            kicker="Bức xạ",
        )

    cols = st.columns(3)
    with cols[0]:
        placeholder_box("Áp suất", "Biểu đồ sẽ được bổ sung.")
    with cols[1]:
        placeholder_box("Tốc độ gió", "Biểu đồ sẽ được bổ sung.")
    with cols[2]:
        placeholder_box("Chỉ số tổng hợp", "Biểu đồ sẽ được bổ sung.")
