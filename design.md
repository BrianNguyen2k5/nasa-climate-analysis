# Vietnam Climate Explorer - Design Notes

## Mục tiêu giao diện

Dashboard được thiết kế như một khung phân tích học thuật cho chủ đề:

> Phân tích và so sánh đặc điểm khí hậu giữa 7 nhóm vùng và 20 điểm tham chiếu tại Việt Nam trong giai đoạn 1991-2025.

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
- Thanh trượt giai đoạn phân tích dùng màu xanh dương cho track và nút kéo; chữ năm giữ màu chữ chính, không chuyển sang màu xanh.
- Bộ lọc hiện chỉ phục vụ bố cục, chưa liên kết với dữ liệu hoặc biểu đồ.

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
- Nếu cần truyền giá trị filter vào từng tab, tạo một cấu trúc `filters` trong `sidebar.py` hoặc `app.py` sau khi nhóm thống nhất giao diện hàm.
