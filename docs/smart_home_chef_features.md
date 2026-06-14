# CẤU TRÚC TÍNH NĂNG HỆ THỐNG SMART HOME CHEF

Dưới đây là cấu trúc chi tiết 6 nhóm tính năng cốt lõi của hệ thống **Smart Home Chef**, được trình bày tương tự theo cấu hình sơ đồ phân nhánh của mẫu Hệ thống Giám sát Khách sạn Sinh viên:

---

## 🎯 TRUNG TÂM: HỆ THỐNG TRỢ LÝ NỘI TRỢ THÔNG MINH (SMART HOME CHEF)

### 1. 🔑 Đăng nhập & Phân quyền
* **Xác thực đa phương thức:** Hỗ trợ đăng nhập truyền thống và liên kết tài khoản qua Google OAuth2.
* **Phân quyền người dùng:** 2 vai trò rõ rệt: **Thành viên (User)** (lập thực đơn, chat, quản lý sức khỏe) và **Quản trị viên (Admin)** (duyệt thực phẩm, giám sát mô hình AI).
* **Quản lý tài khoản:** Quản trị viên có quyền khóa/mở tài khoản thành viên và theo dõi hoạt động người dùng.

### 2. 💬 Trợ lý Chatbot AI
* **Phân loại ý định (Intent Classifier):** Tự động phát hiện ý định hỏi đáp của người dùng bằng mô hình học máy cục bộ (Naive Bayes).
* **Phản hồi ngôn ngữ tự nhiên:** Tự động gọi **Google Gemini API** làm fallback khi người dùng hỏi các câu tự do nằm ngoài dữ liệu cục bộ.
* **Quản lý phiên hội thoại:** Lưu trữ toàn bộ lịch sử trò chuyện, ghi log các ý định phục vụ quá trình tự học của hệ thống.

### 3. ⚖️ Cá nhân hóa & Lập thực đơn
* **Tính điểm tương thích $S(u, f)$:** Tự động chấm điểm các món ăn dựa trên chỉ số cơ thể BMI, mức độ hoạt động và ngân sách chi tiêu.
* **Lọc ràng buộc bệnh nền:** Tự động loại bỏ hoàn toàn các thực phẩm cấm kỵ đối với các bệnh lý đã khai báo (Tiểu đường, Gút, dị ứng Lactose).
* **Tự động lên thực đơn:** Lập kế hoạch ăn uống theo ngày hoặc theo tuần đảm bảo cân đối Calo mục tiêu.

### 4. 🍳 Gợi ý công thức & Biến thể
* **Tìm kiếm theo nguyên liệu có sẵn:** Gợi ý các món ăn tối ưu nhất dựa trên danh sách nguyên liệu hiện có trong tủ lạnh.
* **Sinh công thức tự động:** Sử dụng AI để sinh hướng dẫn nấu ăn chi tiết, thời gian thực hiện và định lượng nguyên liệu.
* **Tự động tạo biến thể công thức:** Chuyển đổi công thức gốc sang các chế độ ăn kiêng khác nhau (Keto, thuần chay, giảm đường, ít béo).

### 5. 📊 Thống kê & Nhật ký dinh dưỡng
* **Nhật ký dinh dưỡng (Nutrition Log):** Ghi chép lượng calo và các chất đa lượng (Carb, Protein, Fat) nạp vào từ các bữa ăn thực tế.
* **Biểu đồ trực quan:** Trực quan hóa tiến trình dinh dưỡng theo ngày, tuần, tháng bằng biểu đồ trực quan (Chart.js).
* **Lịch sử & Log học máy:** Lưu trữ nhật ký đề xuất món ăn và phản hồi của người dùng (like/dislike) để huấn luyện lại AI.

### 6. 🛒 Quản lý bếp & Đi chợ
* **Tủ lạnh ảo (Virtual Fridge):** Quản lý tồn kho thực phẩm hiện có tại nhà và tự động gửi cảnh báo thực phẩm sắp hết hạn.
* **Tự động lập danh sách đi chợ:** Phân tích nguyên liệu còn thiếu từ thực đơn tuần để tự động xuất danh sách mua sắm (Shopping List).
* **Ước tính chi phí:** Ước lượng ngân sách mua sắm dựa trên cơ sở dữ liệu giá cả thực phẩm được crawl thực tế từ thị trường.
