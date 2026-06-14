# BẢN ĐỒ ĐƯỜNG LỐI (ROADMAP) VÀ HƯỚNG PHÁT TRIỂN CHI TIẾT
## ĐỀ TÀI: NGHIÊN CỨU VÀ PHÁT TRIỂN ỨNG DỤNG WEB TRỢ LÝ NỘI TRỢ THÔNG MINH DỰA TRÊN PHÂN TÍCH DỮ LIỆU VÀ CÁ NHÂN HÓA THỰC ĐƠN SỬ DỤNG DJANGO VÀ POSTGRESQL

---

## 1. Định Vị Đề Tài Đạt Chuẩn Đồ Án Tốt Nghiệp

Để một đề tài phát triển ứng dụng web được hội đồng tốt nghiệp đánh giá cao (đạt điểm giỏi/xuất sắc), nó không được chỉ dừng lại ở mức **"CRUD app thông thường"** (thêm, sửa, xóa dữ liệu). Nó cần phải thể hiện rõ:
1. **Tính Khoa Học & Cơ Sở Lý Thuyết**: Có mô hình toán học rõ ràng cho việc phân tích dữ liệu và cá nhân hóa thực đơn (hệ thống gợi ý - Recommender System).
2. **Độ Phức Tạp Kỹ Thuật**: Kiến trúc hệ thống phân lớp sạch sẽ (Clean Architecture), tích hợp Hybrid AI (local processing + LLM fallback), và xử lý tối ưu hóa database (PostgreSQL).
3. **Quy Trình Xử Lý Dữ Liệu Thực Tế**: Có pipeline thu thập dữ liệu (ETL / Crawler) tự động, chuẩn hóa dữ liệu thực phẩm (Data Governance) và luồng phê duyệt (Audit & Approval).
4. **An Toàn & Bảo Mật**: Phân quyền chi tiết, bảo vệ thông tin sức khỏe cá nhân (User Isolation), chống rò rỉ dữ liệu giữa các tài khoản.

---

## 2. Mô Hồi Toán Học Cá Nhân Hóa Thực Đơn (Tăng Tính Khoa Học Cho Đồ Án)

Để chứng minh "phần nghiên cứu" trong đề tài, bạn cần đưa mô hình này vào báo cáo tốt nghiệp và hiện thực hóa nó trong code dịch vụ:

Hàm tối ưu hóa điểm đề xuất $S(u, f)$ cho người dùng $u$ đối với món ăn/thực phẩm $f$:

$$S(u, f) = w_{pref} \cdot P(u, f) + w_{health} \cdot H(u, f) + w_{budget} \cdot B(u, f) - w_{recency} \cdot R(u, f)$$

Trong đó:
*   **$P(u, f) \in [0, 1]$ (Mức độ ưa thích ẩm thực)**:
    Tính bằng độ tương đồng Jaccard giữa danh mục ưa thích trong hồ sơ sở thích $UserProfile.preferred\_categories$ và danh mục món ăn.
    $$P(u, f) = \frac{|Categories(f) \cap Preferred(u)|}{|Categories(f) \cup Preferred(u)|}$$
*   **$H(u, f) \in [-1, 1]$ (Độ tương thích sức khỏe & dinh dưỡng)**:
    *   Cộng điểm nếu thực phẩm phù hợp mục tiêu sức khỏe (ví dụ: Calo thấp $\le 300kcal$ cho mục tiêu giảm cân `weight_loss`).
    *   **Quy tắc loại trừ tuyệt đối (Hard Constraints)**: Nếu thực phẩm $f$ chứa nguyên liệu kỵ với bệnh lý nền $UserDisease$ của $u$ (ví dụ: tiểu đường kỵ đường cát/tinh bột tinh chế; cao huyết áp kỵ muối nồng độ cao), hệ thống lập tức thiết lập $S(u, f) = -\infty$ (Loại bỏ khỏi thực đơn).
*   **$B(u, f) \in [0, 1]$ (Khả năng đáp ứng ngân sách)**:
    Tỷ lệ chi phí ước tính của thực phẩm so với hạn mức ngân sách hàng ngày $UserProfile.budget\_limit$:
    $$B(u, f) = \begin{cases} 1 & \text{nếu } Cost(f) \le Budget(u) \\ e^{-\lambda (Cost(f) - Budget(u))} & \text{nếu } Cost(f) > Budget(u) \end{cases}$$
*   **$R(u, f) \in [0, 1]$ (Hệ số phạt ăn lặp lại - Recency Penalty)**:
    Để tránh việc thực đơn đề xuất cùng 1 món ăn liên tục trong nhiều ngày. Phạt nặng nếu món ăn xuất hiện trong lịch sử ăn uống gần đây ($NutritionLog$ trong vòng 3 ngày qua) và giảm dần theo thời gian.
    $$R(u, f) = \frac{1}{\Delta t + 1} \text{ với } \Delta t \text{ là số ngày tính từ lần ăn gần nhất.}$$

---

## 3. Danh Mục Chi Tiết Các Phần Cần Cải Thiện & Thêm Mới

Dựa trên cấu trúc codebase hiện tại của bạn (`apps/` và `app/services/`), dưới đây là danh sách những phần cần nâng cấp để dự án đạt độ chín chắn cao nhất:

### 3.1. Phân Hệ Dữ Liệu & Data Pipeline (PostgreSQL)
*   **[Thêm mới] Nâng Cấp PostgreSQL Full-Text Search hoặc PGVector**:
    *   Hiện tại, việc tìm kiếm thực phẩm và từ khóa tránh chủ yếu là so khớp chuỗi bằng lệnh `__contains` thô sơ của ORM.
    *   *Nâng cấp*: Cấu hình PostgreSQL Full-Text Search (sử dụng `SearchVector` và `SearchQuery` của Django) để tìm kiếm không dấu, đồng nghĩa.
    *   *Đồ án tốt nghiệp nâng cao*: Cài đặt extension `pgvector` vào PostgreSQL để lưu trữ vector biểu diễn của món ăn và tìm kiếm tương đồng ngữ nghĩa.
*   **[Cải thiện] Pipeline Crawler Tự Động & Bảng Giá Phức Tạp**:
    *   Đảm bảo script crawler WinMart chạy ngầm định kỳ thông qua Celery Worker hoặc Cron Job.
    *   Mở rộng crawler cho tối thiểu 2 nguồn (ví dụ WinMart & Bách Hóa Xanh) để có cơ chế so sánh giá tốt nhất cho người dùng.
*   **[Cải thiện] Hàng Đợi Duyệt Dữ Liệu (Data Steward Approval Queue)**:
    *   Hiện thực hóa giao diện Admin cho bảng `food_verification_queue`. 
    *   Data Steward có thể xem các món ăn mới crawl về, nhấn "Duyệt" (chuyển vào bảng chính `foods`) hoặc "Merge" (nếu phát hiện trùng lặp sản phẩm).
    *   Tự động ghi `audit_logs` khi có hành động sửa đổi dữ liệu cốt lõi.

### 3.2. Phân Hệ Trí Tuệ Nhân Tạo & Cá Nhân Hóa (Hybrid AI)
*   **[Thêm mới] Semantic Intent Classifier (NLU bằng Vector Embedding)**:
    *   Hiện tại, việc phân loại ý định chat trong `classify_intent` đang dùng keyword matching cơ bản.
    *   *Nâng cấp*: Sử dụng bảng `intent_embeddings` đã có. Khi người dùng nhập tin nhắn, hệ thống gọi API sinh vector embedding (hoặc model cục bộ nhẹ), tính khoảng cách Cosine với các mẫu câu hỏi huấn luyện đã seed để chọn ra Intent có độ tương đồng cao nhất.
*   **[Thêm mới] Feedback Loop tự học (Reinforcement Recommendation)**:
    *   Tạo background task định kỳ phân tích hành vi của người dùng (ví dụ: đánh giá món ăn `UserFeedbackFood` hay chọn/bác bỏ thực đơn đề xuất `UserFeedbackRecommendation`).
    *   Cập nhật tự động trọng số ưu thích của người dùng trong bảng `user_preference_profiles` (ví dụ: nếu user nhấn "Thích" món gà 3 lần, tăng điểm ưu tiên đối với danh mục "Gà").
*   **[Thêm mới] Ma Trận Tương Kỵ Thực Phẩm (Incompatibility Matrix)**:
    *   Xây dựng bảng quan hệ `FoodIncompatibility` (Món A kỵ với nguyên liệu B, hoặc nguyên liệu A kỵ nguyên liệu B - ví dụ: mật ong kỵ bột sắn dây).
    *   Khi AI tạo công thức nấu ăn hoặc đề xuất Meal Plan, hệ thống phải tự động quét qua ma trận tương kỵ này để đưa ra cảnh báo an toàn sức khỏe cho người dùng.

### 3.3. Bảo Mật Hệ Thống & Bảo Vệ Dữ Liệu (Security & Tenant Isolation)
*   **[Cải thiện] Khắc Phục Triệt Để Rò Rỉ Dữ Liệu (Critical Security Patch)**:
    *   Áp dụng các bản vá bảo mật (chặn rò rỉ dữ liệu lịch sử chat và lập thực đơn). 
    *   Viết lại các truy vấn DB (QuerySets) sử dụng bộ lọc luôn gắn chặt với `request.user` (ví dụ: `MealPlan.objects.filter(account=request.user)` thay vì cho phép ID rỗng hoặc bỏ sót kiểm tra quyền sở hữu).
*   **[Cải thiện] Tích Hợp Đăng Nhập Mạng Xã Hội Đầy Đủ**:
    *   Cấu hình hoàn chỉnh OAuth2 (Đăng nhập bằng Google/Facebook) thông qua `django-allauth`.
    *   Xử lý đồng bộ thông tin hồ sơ sức khỏe cơ bản ngay sau khi người dùng đăng nhập Google lần đầu.

### 3.4. Giao Diện Người Dùng (Premium UI/UX)
*   **[Cải thiện] Thiết Kế UI/UX Theo Phong Cách Hiện Đại (Wow Factor)**:
    *   Sử dụng CSS mượt mà kết hợp các biểu đồ trực quan (ví dụ: Chart.js hoặc ApexCharts) để hiển thị biểu đồ calo nạp vào hàng ngày, tỷ lệ macronutrients (Carbs - Protein - Fat).
    *   Tối ưu hóa giao diện Chatbot: Hiển thị hiệu ứng gõ chữ (typing indicator), hiển thị đề xuất món ăn dạng slide hoặc card đẹp mắt, hỗ trợ xuất shopping list ra PDF/file ảnh bằng 1 click.
*   **[Thêm mới] Dashboard Cho Data Steward**:
    *   Xây dựng một giao diện Admin trực quan hiển thị chất lượng dữ liệu: Tỷ lệ món ăn thiếu chỉ số dinh dưỡng, biểu đồ biến động giá của WinMart, số lượng sản phẩm đang chờ duyệt trong hàng đợi.

---

## 4. Lộ Trình Phát Triển Chi Tiết (5 Giai Đoạn)

Để hoàn thiện dự án này trong thời gian làm đồ án (thường từ 3 - 6 tháng), bạn nên chia thành 5 giai đoạn rõ ràng:

### Giai Đoạn 1: Củng Cố Database & Data Pipeline (Thời gian gợi ý: 2-3 tuần)
1.  **Thiết lập PostgreSQL**: Cấu hình PostgreSQL làm database chính thức (thay cho SQLite dùng trong phát triển).
2.  **Hoàn thiện Crawler WinMart**: Viết scheduler chạy crawler tự động vào 2h sáng mỗi ngày, ghi nhận giá sản phẩm (`food_prices`).
3.  **Tích hợp Verification Queue**: Thiết lập màn hình kiểm duyệt dữ liệu thô dành cho Data Steward, hỗ trợ gán danh mục chuẩn (canonical category) và đánh giá chất lượng dinh dưỡng trước khi duyệt.
4.  **Kiểm tra tính toàn vẹn**: Chạy script validate dữ liệu đảm bảo không còn bản ghi trùng lặp tên/nhãn dinh dưỡng.

### Giai Đoạn 2: Xây Dựng Thuật Toán Cá Nhân Hóa & Hybrid AI (Thời gian gợi ý: 3-4 tuần)
1.  **Cài đặt Hàm Tối Ưu Hóa Dinh Dưỡng**: Viết service `personalization_service.py` hiện thực hóa đầy đủ công thức toán học $S(u,f)$ bao gồm điểm Calo, Bệnh lý nền (lọc kỵ), Ngân sách, và Recency Penalty.
2.  **Nâng cấp Semantic Intent**: Sử dụng Hugging Face Transformers hoặc OpenAI/Gemini Embeddings để thực hiện semantic search cho câu hỏi của người dùng, ánh xạ chính xác vào các intent đã định nghĩa (Meal Plan, Nutrition Info, General Chat).
3.  **Hoàn thiện Meal Plan Generator**: Cho phép tạo thực đơn tuần tự động dựa trên cấu hình calo đích, phân bổ calo theo tỷ lệ 30% sáng - 40% trưa - 30% tối.

### Giai Đoạn 3: Phát Triển UI/UX Premium Cho Người Dùng & Admin (Thời gian gợi ý: 3 tuần)
1.  **Dashboard Dinh Dưỡng**: Màn hình chính của người dùng trực quan, vẽ biểu đồ mục tiêu dinh dưỡng vs. thực tế đã ăn (`NutritionLog`).
2.  **Ứng Dụng Chat Chuyên Nghiệp**: Tích hợp giao diện bong bóng chat hiện đại, hỗ trợ stream câu trả lời và hiển thị đính kèm thẻ món ăn (Food Cards) có hình ảnh sinh động.
3.  **Giao diện Quản Trị Mô Hình (Model Manager)**: Cho phép admin theo dõi số lượt gọi API Gemini, thống kê chi phí, tỷ lệ hit-rate của Similarity Cache.

### Giai Đoạn 4: Bảo Mật, Kiểm Thử & Tối Ưu Hiệu Năng (Thời gian gợi ý: 2 tuần)
1.  **Bảo Mật Truy Cập**: Rà soát và áp dụng phân quyền (Decorator `@login_required` và kiểm tra quyền sở hữu bản ghi) cho tất cả các endpoint API.
2.  **Similarity Cache TTL & Debounce**: Tối ưu hóa cache phản hồi chatbot để tránh spam API làm cạn kiệt tài khoản Gemini.
3.  **Kiểm thử tự động (Unit & Integration Tests)**: Viết test suite bao phủ toàn bộ luồng tạo thực đơn, kiểm duyệt món ăn và phân biệt Intent chat. Đảm bảo tỷ lệ bao phủ code (code coverage) trên 80%.

### Giai Đoạn 5: Đánh Giá Khoa Học & Viết Báo Cáo Tốt Nghiệp (Thời gian gợi ý: 3-4 tuần)
1.  **Đo lường & Đánh giá (Evaluation Metrics)**:
    *   Đo lường độ chính xác của bộ phân loại Intent (vẽ ma trận nhầm lẫn - Confusion Matrix).
    *   Đo lường hiệu quả tiết kiệm chi phí của Similarity Cache (vẽ biểu đồ số lượt gọi Gemini tiết kiệm được).
    *   Đo lường tốc độ phản hồi (Latency) khi có và không có Cache.
2.  **Vẽ Sơ Đồ Kiến Trúc Chuyên Nghiệp**: Sử dụng mô hình C4 (C4 Model) hoặc UML chuẩn để vẽ:
    *   Sơ đồ thực thể liên kết (ERD) hoàn chỉnh của cơ sở dữ liệu.
    *   Sơ đồ các ca sử dụng (Use Case Diagram).
    *   Sơ đồ tuần tự (Sequence Diagram) cho luồng lập thực đơn cá nhân hóa.
3.  **Soạn thảo Báo cáo Đồ án tốt nghiệp**: Cấu trúc báo cáo theo chuẩn khoa học (Đặt vấn đề -> Cơ sở lý thuyết -> Phân tích thiết kế -> Hiện thực hóa -> Đánh giá kết quả -> Kết luận & Hướng phát triển).

---

## 5. Cấu Trúc Báo Cáo Đồ Án Tốt Nghiệp Gợi Ý (Dành Cho Viết Luận Văn)

Để báo cáo đạt chuẩn khoa học, bạn nên thiết kế cấu trúc chương như sau:

*   **MỞ ĐẦU**: Lý do chọn đề tài, mục tiêu, phạm vi nghiên cứu, phương pháp thực hiện và cấu trúc luận văn.
*   **CHƯƠNG 1: CƠ SỞ LÝ THUYẾT & CÔNG NGHỆ**:
    *   Lý thuyết về Hệ gợi ý (Recommender System), lọc cộng tác (Collaborative Filtering) và lọc dựa trên nội dung (Content-based Filtering).
    *   Khái quát về Mô hình ngôn ngữ lớn (LLM), kỹ thuật Prompt Engineering và Hybrid AI.
    *   Giới thiệu công nghệ cốt lõi: Python, Django, PostgreSQL, Google Gemini API.
*   **CHƯƠNG 2: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG**:
    *   Đặc tả tác nhân (Actors) và biểu đồ Use Case tổng thể cùng 7 Use Case chi tiết.
    *   Thiết kế kiến trúc hệ thống (Kiến trúc phân lớp sạch - Clean Architecture).
    *   Thiết kế Cơ sở dữ liệu (ERD chi tiết, mô tả các bảng cốt lõi và mối liên kết).
*   **CHƯƠNG 3: MÔ HÌNH TOÁN HỌC & GIẢI THUẬT CÁ NHÂN HÓA**:
    *   Chi tiết hóa công thức tối ưu hóa điểm số thực đơn $S(u, f)$.
    *   Thiết kế thuật toán lọc ràng buộc cứng (bệnh lý, dị ứng) và sắp xếp đa mục tiêu (dinh dưỡng, chi phí, sự đa dạng món ăn).
    *   Thiết kế luồng xử lý NLU (Semantic Intent Recognition) và cơ chế bộ đệm tương đồng (Similarity Cache).
*   **CHƯƠNG 4: HIỆN THỰC HÓA VÀ KẾT QUẢ ĐẠT ĐƯỢC**:
    *   Chi tiết về môi trường phát triển và triển khai hệ thống (Nginx, Gunicorn, PostgreSQL).
    *   Mô tả các giao diện chính của hệ thống kèm hình ảnh minh họa (Dashboard người dùng, Chatbot AI, Trang quản trị Data Steward, Verification Queue).
*   **CHƯƠNG 5: THỬ NGHIỆM VÀ ĐÁNH GIÁ**:
    *   Kịch bản kiểm thử các chức năng cốt lõi (Unit test & Integration test).
    *   Đánh giá hiệu năng hệ thống (Độ trễ phản hồi chat, tỷ lệ hit-rate của Cache, tính ổn định khi mất kết nối LLM).
    *   Khảo sát mức độ hài lòng của người dùng thực tế đối với thực đơn được cá nhân hóa.
*   **KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN**: Tổng kết những nội dung đã làm được, tự đánh giá ưu khuyết điểm và vạch ra các hướng nghiên cứu sâu hơn trong tương lai.
