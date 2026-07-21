# HƯỚNG DẪN TÍCH HỢP AI

## 1. Yêu cầu tích hợp AI
Tích hợp tính năng AI vào phân tích dữ liệu: có thể là ứng dụng độc lập hoặc tích hợp vào dashboard hoặc tạo API để các ứng dụng khác sử dụng. 
*(Khuyến khích tạo API để các ứng dụng khác sử dụng).*

### 1.1. Nguyên tắc cơ bản

*   **AI đóng vai trò:**
    *   Trợ giúp đề xuất ý tưởng.
    *   Viết code dựa vào yêu cầu của người dùng.
    *   Trình bày kết quả phân tích với số liệu và hình ảnh, biểu đồ được cung cấp bởi con người, **không được tự ý thêm số liệu hay hình ảnh khác**.
*   **Con người đóng vai trò:**
    *   Định hướng, đề xuất các yêu cầu phân tích, ra quyết định thực thi code.
    *   Nếu con người chưa biết, chưa có ý tưởng về cách phân tích như thế nào thì có thể yêu cầu AI đưa ra các gợi ý, phương pháp để con người lựa chọn.
*   **Thực thi code:** Phải trên môi trường local của người dùng. **Không được thực thi trên môi trường online**.

---

## 2. Nguyên tắc “Không thực thi ngầm”
AI không được phép tự ý thay đổi dữ liệu gốc hay âm thầm chạy các thuật toán.

*   **Hiển thị code bắt buộc:** Mỗi khi AI tạo code theo yêu cầu của con người, nó bắt buộc phải hiển thị rõ ràng.
*   **Giải thích bằng ngôn ngữ tự nhiên:** Ngay trên đoạn code đó, AI phải đính kèm các dòng comment giải thích bằng ngôn ngữ tự nhiên *(Ví dụ: "Đoạn code này sẽ xóa 15 dòng có giá trị NULL ở cột Doanh Thu, sử dụng hàm dropna() của Pandas.")*.

### 2.1. Nguyên tắc phê duyệt
Thể hiện vai trò “Người quyết định”.

*   **Trạng thái chờ:** Code do AI sinh ra ban đầu sẽ ở trạng thái “Chờ duyệt”. Con người có thể thay đổi, bổ sung hoặc loại bỏ code này.
*   **Chỉnh sửa:** Con người có quyền trực tiếp can thiệp, gõ sửa các tham số trong đoạn code AI vừa viết *(Ví dụ: đổi giới hạn outlier từ 3 standard deviations xuống 2)*.
*   **Chấp nhận & thực thi:** Đoạn code chỉ được thực thi và trả về kết quả/biểu đồ khi và chỉ khi con người chấp thuận.

### 2.2. Nguyên tắc lưu trữ
Hệ thống phải lưu trữ tất cả các yêu cầu, mã nguồn, kết quả phân tích và giải thích để có thể truy xuất lại được.

---

## 3. Trong vấn đáp
Các nhóm sẽ được yêu cầu sử dụng module AI đã phát triển để trả lời các câu hỏi phân tích dựa trên dữ liệu của nhóm và các câu hỏi phân tích đã chuẩn bị sẵn, nhằm tránh lan man. Tuy nhiên, vẫn có thể được yêu cầu trả lời câu hỏi ngoài lề để đánh giá mức độ linh hoạt của AI. 

> **Lưu ý:** Số lượng câu hỏi tối thiểu bằng số lượng thành viên trong nhóm.

---

## 4. Trong báo cáo
Phải tóm tắt lại quá trình sử dụng AI, những yêu cầu đã đặt ra, những kết quả đã nhận được, những thay đổi đã thực hiện và những nhận xét về AI.

---

## 5. Gợi ý thiết kế (Phân chia cấu trúc API và Frontend)

### 5.1. Phần Giao diện & Tương tác người dùng (Frontend)
Công nghệ phát triển giao diện Frontend là tùy chọn *(có thể dùng Streamlit, Gradio, React, hoặc các công cụ Dashboard có khả năng tương tác, ...)*. Các nhóm chỉ cần đảm bảo các chức năng cơ bản. Khuyến khích các nhóm tạo ra những giao diện đẹp, trực quan, dễ sử dụng cho người dùng.

*   **Chức năng nhận yêu cầu:** Một ô chat hoặc form nhập liệu để người dùng gửi yêu cầu phân tích/viết code cho AI.
*   **Chức năng xem & chỉnh sửa mã nguồn.**
*   **Chức năng phê duyệt.**
*   **Chức năng hiển thị kết quả.**

### 5.2. Phần API

*   **API AI (Bắt buộc):**
    *   Tiếp nhận yêu cầu từ Frontend.
    *   Gửi kèm ngữ cảnh *(ví dụ: cấu trúc dữ liệu hiện có)* cho mô hình AI (Gemini/OpenAI/Local model).
    *   Yêu cầu AI trả về cả code và giải thích tương ứng; hoặc kết quả trình bày.
*   **API Thực thi (Bắt buộc):**
    *   Tiếp nhận đoạn mã đã được con người “chỉnh sửa” và “phê duyệt” từ Frontend.
    *   Thực hiện chạy code trực tiếp trên dữ liệu tại máy (local).
    *   Thu thập kết quả *(ảnh biểu đồ, bảng dữ liệu, logs)* để trả về cho Frontend hiển thị.
*   **API Logs (Bắt buộc):**
    *   Lưu trữ tất cả các yêu cầu, mã nguồn, kết quả phân tích và giải thích.