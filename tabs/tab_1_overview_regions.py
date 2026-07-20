import streamlit as st


REGIONS = [
    "Tây Bắc",
    "Đông Bắc",
    "Đồng bằng Bắc Bộ",
    "Bắc Trung Bộ",
    "Nam Trung Bộ",
    "Tây Nguyên",
    "Nam Bộ",
]


def render_overview_regions_tab(placeholder_box) -> None:
    st.markdown('<div class="section-title">Tổng quan 7 nhóm vùng khí hậu</div>', unsafe_allow_html=True)
    st.markdown(
        " ".join(f'<span class="region-chip">{region}</span>' for region in REGIONS),
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.35, 1])
    with left:
        placeholder_box(
            "Bản đồ phân vùng khí hậu Việt Nam",
            "Biểu đồ sẽ được bổ sung: bản đồ hoặc lớp trực quan thể hiện 7 nhóm vùng và 20 điểm tham chiếu.",
            kicker="Không gian",
            tall=True,
        )
    with right:
        placeholder_box(
            "Hồ sơ khí hậu theo vùng",
            "Biểu đồ sẽ được bổ sung: bảng tóm tắt đặc trưng nhiệt, mưa, ẩm và mùa khí hậu.",
            kicker="Tổng hợp",
        )
        st.write("")
        placeholder_box(
            "Xếp hạng khác biệt vùng",
            "Biểu đồ sẽ được bổ sung: mức tương phản giữa các vùng trong giai đoạn 1991-2025.",
            kicker="So sánh",
        )

    st.markdown('<div class="section-title">Khung phân tích vùng</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]:
        placeholder_box("Phân bố điểm tham chiếu", "Biểu đồ sẽ được bổ sung.")
    with cols[1]:
        placeholder_box("Tín hiệu khí hậu nổi bật", "Biểu đồ sẽ được bổ sung.")
    with cols[2]:
        placeholder_box("Ghi chú học thuật", "Container dành cho nhận xét và diễn giải sau khi có dữ liệu.")
