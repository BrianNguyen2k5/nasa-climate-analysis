# Vietnam Climate Explorer - Design Notes

## Mục tiêu giao diện

Dashboard được thiết kế như một khung phân tích học thuật cho chủ đề:

> Phân tích đặc điểm khí hậu giữa 6 nhóm vùng và 20 điểm tham chiếu tại Việt Nam trong giai đoạn 1991-2025.

Ở giai đoạn hiện tại, dashboard chỉ dựng sườn giao diện. Các vùng trực quan hóa được để dưới dạng placeholder để có thể thay bằng biểu đồ thật khi hoàn thiện phần đọc dữ liệu, xử lý dữ liệu và phân tích.

## Cấu trúc file

- `app.py`: file chạy chính, cấu hình trang, CSS nội dung chính, header, metric tổng quan và điều phối tab đang chọn.
- `sidebar.py`: điều hướng sidebar, bộ lọc `Vùng`, `Địa điểm`, `Giai đoạn phân tích` và CSS riêng của sidebar.
- `tabs/tab_1_overview_regions.py`: tab Tổng quan.
- `tabs/tab_2_temperature_comparison.py`: tab Nhiệt độ.
- `tabs/tab_3_rainfall_humidity.py`: tab Mưa và độ ẩm.
- `tabs/tab_4_meteorological_factors.py`: tab Yếu tố khí tượng.
- `tabs/tab_5_extreme_weather.py`: tab Thời tiết cực đoan.
- `tabs/tab_6_ai_assistant.py`: tab AI, hiện là placeholder và chưa gọi API.
- `tabs/__init__.py`: đánh dấu thư mục `tabs` là package Python.

## Sidebar

- Tab dashboard nằm trong sidebar, phía trên bộ lọc.
- Sidebar dùng `st.radio` để chọn tab đang hiển thị, nhưng CSS ẩn ô tròn radio mặc định để tab nhìn như nút điều hướng.
- Tab được trình bày full-width, cùng chiều ngang; tab đang chọn dùng màu xanh dương chính `#1E3A5F`.
- Bộ lọc hiện có: `Vùng`, `Địa điểm`, `Giai đoạn phân tích`.
- Các vùng trong dataset mới gồm 6 nhóm, hiển thị trực tiếp bằng tiếng Việt:
  - `Bắc Trung Bộ`
  - `Nam Trung Bộ`
  - `Trung du và miền núi phía Bắc`
  - `Đông Nam Bộ`
  - `Đồng bằng sông Cửu Long`
  - `Đồng bằng sông Hồng`
- Khi chọn một vùng, danh sách `Địa điểm` chỉ hiển thị các điểm tham chiếu thuộc vùng đó.
- Bộ lọc đang được dùng cho tab Tổng quan để lọc KPI và bản đồ theo `Vùng`, `Địa điểm` và `Giai đoạn phân tích`.

## KPI Tab Tổng Quan

Tab Tổng quan có 5 KPI card đổi ý nghĩa theo phạm vi filter:

- Khi chọn `Tất cả 6 nhóm vùng` và không chọn địa điểm: KPI là xếp hạng toàn quốc, ví dụ vùng nóng nhất, vùng mưa nhiều nhất, vùng ẩm nhất.
- Khi chọn một vùng và không chọn địa điểm: KPI là đặc điểm khí hậu của vùng đang chọn.
- Khi chọn một hoặc nhiều địa điểm: KPI là đặc điểm khí hậu của điểm tham chiếu hoặc nhóm điểm đang chọn.

Tab Tổng quan hiện đã đọc dữ liệu thật từ `data/nasa_power_vietnam_daily_clean.csv` để tính 5 KPI và tooltip bản đồ. Các chỉ số dùng các cột `T2M`, `PRECTOTCORR`, `RH2M`, `hot_day`, `heavy_rain_day`, có áp dụng filter `Vùng`, `Địa điểm` và `Giai đoạn phân tích`.

Cột phải của tab Tổng quan có line chart xu hướng theo năm, cho phép chọn `Nhiệt độ`, `Độ ẩm` hoặc `Lượng mưa`; biểu đồ dùng cùng filter sidebar với KPI và bản đồ.

Bên dưới line chart là bar ngang xếp hạng địa điểm. Trục y là `Tỉnh/thành`, trục x là biến được chọn (`Nhiệt độ`, `Độ ẩm`, `Lượng mưa`); mặc định hiển thị top 5 giảm dần, còn khi sidebar chọn địa điểm thì hiển thị các địa điểm đang lọc. Các placeholder dưới cùng của tab Tổng quan đã được bỏ để tập trung vào KPI, bản đồ và hai biểu đồ bên phải.

Bản đồ trong tab Tổng quan được render bằng `folium` và `streamlit-folium`, dùng các điểm tham chiếu thật từ NASA POWER. Chú thích bản đồ được nhúng bằng HTML/CSS gọn trong góc phải, giải thích màu theo nhiệt độ, kích thước theo số ngày nóng và cảnh báo cực đoan.

## Bảng màu

- Màu chính: `#1E3A5F`
- Màu phụ: `#2A9D8F`
- Màu nhấn nhiệt độ: `#F4A261`
- Màu nhấn cực đoan: `#E76F51`
- Nền chính: `#F5F7FA`
- Nền thẻ: `#FFFFFF`
- Chữ chính: `#1F2937`
- Chữ phụ: `#64748B`
- Đường viền: `#E2E8F0`

## Quy ước chia việc để hạn chế conflict

Mỗi thành viên phụ trách một tab chính và chỉ sửa file tab tương ứng:

- Thành viên 1: `tabs/tab_1_overview_regions.py`
- Thành viên 2: `tabs/tab_2_temperature_comparison.py`
- Thành viên 3: `tabs/tab_3_rainfall_humidity.py`
- Thành viên 4: `tabs/tab_4_meteorological_factors.py`
- Thành viên 5: `tabs/tab_5_extreme_weather.py`

Quy ước làm nhóm:

- Không sửa `app.py` nếu chỉ thêm nội dung, biểu đồ hoặc phân tích cho một tab đã tồn tại.
- Nếu cần chỉnh sidebar, chỉ sửa `sidebar.py`.
- Không đổi tên hàm render chính trong từng tab.
- Nếu cần helper riêng cho một tab, đặt helper trong chính file tab đó hoặc tạo thư mục con riêng theo tên tab.
- Tab AI nằm ở `tabs/tab_6_ai_assistant.py` và là phần mở rộng riêng, không nằm trong phạm vi 5 tab chính của 5 thành viên.

## Hướng mở rộng

- Thay `placeholder_box(...)` bằng biểu đồ thật trong từng file tab.
- Giữ sidebar làm nguồn trạng thái filter chung.
- Tách các hàm đọc dữ liệu, tiền xử lý và tính chỉ số sang module riêng để `app.py` chỉ giữ vai trò điều phối giao diện.
- Khi có dữ liệu thật, thay các KPI placeholder trong tab Tổng quan bằng kết quả tính toán theo `region`, `locations` và `period` từ `sidebar.py`.