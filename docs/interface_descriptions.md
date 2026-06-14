# MÔ TẢ GIAO DIỆN HỆ THỐNG SMART HOME CHEF

Dưới đây là mô tả chi tiết, đơn giản và chuyên nghiệp cho 3 giao diện chính của hệ thống **Smart Home Chef** (phục vụ viết thuyết minh đồ án hoặc slide thuyết trình):

---

## 1. GIAO DIỆN TỔNG QUAN (NUTRITION DASHBOARD)
* **Mục đích:** Là màn hình trung tâm giúp người dùng theo dõi và kiểm soát toàn bộ trạng thái dinh dưỡng cá nhân trong ngày.
* **Các thành phần chính:**
  * **Thẻ chỉ số dinh dưỡng:** Hiển thị thời gian thực lượng Calo (Kcal), chất đạm (Protein), chất bột đường (Carbs) và chất béo (Fat) đã nạp vào cơ thể kèm theo tỷ lệ phần trăm so với mục tiêu đề ra.
  * **Bảng thống kê nhanh:** Hiển thị số ngày ăn kiêng tích lũy, số nhật ký ăn uống trong ngày, số lượng thực đơn tuần đã lập và tổng số món ăn hiện có trong cơ sở dữ liệu.
  * **Biểu đồ so sánh:** Cung cấp bảng đối chiếu chi tiết lượng dinh dưỡng nạp vào hôm nay so với hôm qua và mức trung bình 7 ngày gần nhất để người dùng điều chỉnh hành vi ăn uống kịp thời.

## 2. GIAO DIỆN CHAT (TRỢ LÝ AI COOKING ASSISTANT)
* **Mục đích:** Là kênh giao tiếp trực tiếp bằng ngôn ngữ tự nhiên, nơi người dùng nhận tư vấn dinh dưỡng và gợi ý công thức từ Trợ lý AI.
* **Các thành phần chính:**
  * **Hộp thoại chat:** Hiển thị các phản hồi của AI dưới dạng văn bản định dạng Markdown rõ ràng, hiển thị đầy đủ tiêu đề, nguyên liệu cần chuẩn bị và các bước thực hiện món ăn (ví dụ: công thức món Xôi thịt kho truyền thống).
  * **Hộp nhập liệu câu hỏi:** Nằm ở phía dưới cùng giao diện, cho phép người dùng gõ nhanh các thắc mắc về thực phẩm, nguyên liệu hoặc chế độ ăn kiêng.
  * **Nút chức năng nhanh:** Tích hợp các nút tiện ích như "Xóa lịch sử chat" để bảo mật thông tin và "Xem thực đơn tuần" được liên kết trực tiếp.

## 3. GIAO DIỆN QUẢN TRỊ DỮ LIỆU (ADMIN PANEL)
* **Mục đích:** Là trung tâm điều khiển dành riêng cho Quản trị viên (Admin/Developer) để giám sát tài nguyên hệ thống, quản lý dữ liệu thô và cấu hình mô hình AI.
* **Các thành phần chính:**
  * **Thẻ số liệu tổng quan:** Thống kê số lượng bản ghi thực tế trong cơ sở dữ liệu bao gồm số lượng thực phẩm (Food), số mẫu câu huấn luyện (Pattern), số lượng ý định nhận diện (Intent), và log hội thoại (`MessageIntent`).
  * **Thanh tìm kiếm thông minh:** Cho phép tra cứu nhanh chóng và lọc thông tin chi tiết của tài khoản người dùng, món ăn, công thức và lịch sử chat.
  * **Nút điều phối hệ thống:** Tích hợp các nút công cụ nhanh như "Khởi động crawl" (kích hoạt công cụ thu thập dữ liệu WinMart) và "Tải lại cache" để tối ưu hóa hiệu năng hệ thống.
