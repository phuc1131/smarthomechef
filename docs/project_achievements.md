# CÁC KẾT QUẢ ĐẠT ĐƯỢC CỦA DỰ ÁN SMART HOME CHEF

Dưới đây là tổng hợp các kết quả thực tế đã đạt được (Key Deliverables) của dự án **Smart Home Chef**, được phân loại cụ thể theo từng nhóm chuyên môn kỹ thuật để phục vụ viết báo cáo và thuyết trình đồ án tốt nghiệp:

---

## 📂 NHÓM 1: QUẢN TRỊ & CHUẨN HÓA DỮ LIỆU (DATA GOVERNANCE)
* **Tự động hóa Crawler dữ liệu giá:** Phát triển thành công bộ thu thập dữ liệu (Web Scraper/Crawler) sử dụng BeautifulSoup4 để tự động trích xuất sản phẩm, danh mục và giá tiền thực tế từ hệ thống siêu thị WinMart.
* **Quy trình kiểm duyệt dữ liệu (Verification Queue):** Xây dựng hàng đợi duyệt thực phẩm thô (`food_verification_queue`) dành cho Quản trị viên dữ liệu nhằm chuẩn hóa tên gọi, danh mục và dinh dưỡng trước khi đưa vào cơ sở dữ liệu chính.
* **Ghi nhật ký thay đổi (Audit Logs):** Triển khai log hệ thống ghi nhận toàn bộ hoạt động chỉnh sửa dữ liệu dinh dưỡng, bảo đảm tính toàn vẹn và sạch sẽ của kho dữ liệu.
* **Tích hợp lịch sử giá:** Ánh xạ dữ liệu giá WinMart vào các bảng giá (`food_prices`, `ingredient_prices`) theo thời gian thực để làm cơ sở tính toán chi phí bữa ăn.

## 📂 NHÓM 2: GIẢI PHÁP TRÍ TUỆ NHÂN TẠO HYBRID AI TỐI ƯU
* **Chiến lược Hybrid AI (DB-First, LLM-Fallback):** Xây dựng bộ điều phối `ai_orchestrator_service.py` giúp ưu tiên truy vấn dữ liệu cục bộ trước để trả lời người dùng. Chỉ chuyển tiếp sang Google Gemini API làm fallback khi cần hội thoại tự do hoặc sinh công thức món ăn mới.
* **Bộ đệm độ tương đồng (Similarity Cache):** Tích hợp thuật toán Jaccard Similarity cho Chatbot giúp lưu trữ và tái sử dụng các câu trả lời AI từ lịch sử, giúp **giảm hơn 70% chi phí gọi API Gemini** và giảm độ trễ phản hồi xuống dưới 1 giây.
* **Mô hình học máy cục bộ (Self-Learning):** Huấn luyện mô hình phân loại ý định (Intent Classifier) cục bộ (Naive Bayes) có khả năng tự học và cập nhật từ lịch sử trò chuyện (`ChatMessage`) và các nhãn ý định (`MessageIntent`) do Admin gán.

## 📂 NHÓM 3: CÁ NHÂN HÓA DINH DƯỠNG & HỖ TRỢ Y TẾ
* **Tính toán cá nhân hóa theo thể trạng:** Tự động tính toán lượng Calo đích dựa trên chỉ số BMI, tuổi tác, giới tính và mức độ hoạt động của từng người dùng để đề xuất thực đơn phù hợp.
* **Bộ quy tắc lọc y tế (Disease Constraints):** Thiết lập mô hình liên kết bệnh lý (`diseases`) và quy tắc lọc (`disease_nutrition_rules`), tự động loại bỏ các món ăn nguy hại cho người có bệnh nền (ví dụ: loại bỏ thịt đỏ cho bệnh nhân gút, loại bỏ thực phẩm chứa đường cho người tiểu đường).
* **Tối ưu hóa ngân sách:** Kết hợp giá nguyên liệu thực tế để xếp hạng (Reranking) món ăn, đảm bảo thực đơn tuần của gia đình không vượt quá hạn mức chi tiêu (`budget_limit`) đã thiết lập.

## 📂 NHÓM 4: BẢO MẬT & CÔ LẬP DỮ LIỆU (SECURITY & ISOLATION)
* **Cô lập dữ liệu người dùng (User Isolation):** Khắc phục triệt để lỗi rò rỉ thông tin cá nhân bằng cách phân quyền và lọc chính xác toàn bộ lịch sử chat (`ChatSession`, `ChatMessage`) và lịch sử thực đơn (`MealPlan`) theo `account_id` của từng tài khoản đăng nhập.
* **Phân quyền vai trò hệ thống:** Triển khai phân quyền truy cập chặt chẽ giữa 2 nhóm vai trò: **Thành viên (User)** (chỉ truy cập dữ liệu cá nhân của mình) và **Quản trị viên (Admin)** (có quyền truy cập Dashboard giám sát và cấu hình AI).

## 📂 NHÓM 5: KIẾN TRÚC PHẦN MỀM & KIỂM THỬ (ARCHITECTURE & QUALITY)
* **Tổ chức Clean Architecture theo tính năng (Feature-Based):** Phân rã mã nguồn Django thành 5 ứng dụng độc lập (`users`, `nutrition`, `meal_plans`, `chat`, `core_models`), giúp hệ thống có cấu trúc rõ ràng, dễ bảo trì và mở rộng.
* **Đầy đủ kịch bản kiểm thử tự động (Unit Tests):** Xây dựng hơn 10 bộ kiểm thử tự động (unit tests & integration tests) bao phủ toàn bộ các luồng dịch vụ cốt lõi như: xác thực OAuth2, gợi ý thực đơn tuần, parser nguyên liệu và tích hợp Gemini API.
