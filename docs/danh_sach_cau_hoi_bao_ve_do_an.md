# TÀI LIỆU ÔN TẬP PHẢN BIỆN BẢO VỆ ĐỒ ÁN TỐT NGHIỆP (BẢN ĐẦY ĐỦ NHẤT)
**Đề tài: Nghiên cứu và phát triển ứng dụng Web Trợ lý nội trợ thông minh dựa trên phân tích dữ liệu và cá nhân hóa thực đơn sử dụng Django và PostgreSQL.**

Tài liệu này tổng hợp toàn bộ các câu hỏi có thể xuất hiện trong buổi bảo vệ, từ tổng quan nghiệp vụ, kỹ thuật phần mềm, cho đến thuật toán AI chuyên sâu, giúp bạn tự tin phản biện mọi ngóc ngách của hệ thống.

---

## 📌 CHỦ ĐỀ 1: TỔNG QUAN, MỤC TIÊU VÀ TÍNH THỰC TIỄN (NGHIỆP VỤ)

### 1. Sự khác biệt của "Trợ lý nội trợ thông minh" so với các ứng dụng tra cứu calo hiện có trên thị trường là gì?
Thưa thầy cô, điểm khác biệt lớn nhất nằm ở tính **"Cá nhân hóa"** và **"Tích hợp AI"**. Đa phần các ứng dụng hiện nay (như MyFitnessPal) chỉ là một cuốn từ điển calo thụ động, người dùng phải tự tính toán. Còn hệ thống của em sẽ chủ động đưa ra thực đơn dựa trên Profile (bệnh lý, chiều cao, cân nặng, ngân sách). Đồng thời, Chatbot tích hợp LLM và RAG giúp người dùng hỏi đáp trực tiếp bằng ngôn ngữ tự nhiên thay vì phải click tra cứu thủ công.

### 2. Nếu hệ thống gợi ý món ăn sai, ảnh hưởng sức khỏe người bệnh (VD: tiểu đường) thì xử lý thế nào?
Để giảm rủi ro, hệ thống có hai cơ chế: 
- Kỹ thuật: Hệ thống áp dụng "Ràng buộc cứng" (Hard Constraints). Nếu có bệnh tiểu đường, thuật toán sẽ Filter bỏ các món chứa nguyên liệu cấm kỵ trước khi đưa vào hàm xếp hạng và sinh văn bản.
- UX/Pháp lý: Hệ thống tự động chèn câu Disclaimer *"Thông tin mang tính chất tham khảo, vui lòng hỏi ý kiến bác sĩ"* vào các luồng tư vấn y tế.

### 3. Làm thế nào em đánh giá được AI và module gợi ý đang đem lại sự hài lòng cho người dùng?
Hệ thống sử dụng cơ chế **Vòng lặp phản hồi (Feedback Loop)**. Trong giao diện, người dùng có thể bấm Like/Dislike cho các phản hồi của Bot và thực đơn được tạo. Dữ liệu này được lưu xuống bảng `RecommendationLog` và Dashboard của Admin. Đặc biệt, nếu một món bị Dislike, thuật toán cá nhân hóa sẽ tự động giảm trừ điểm (Penalty) của món đó trong tương lai cho người dùng đó.

### 4. Hệ thống này giải quyết bài toán của người dùng ở Việt Nam như thế nào?
Hệ thống tập trung thu thập, cào dữ liệu và chuẩn hóa các món ăn thuần Việt, nguyên liệu ở siêu thị Việt Nam (như WinMart). Việc tinh chỉnh prompt và xử lý tiếng Việt không dấu trong mô hình Naive Bayes giúp chatbot thân thiện và đáp ứng đúng nhu cầu ẩm thực của người dùng trong nước, thay vì các dữ liệu món Âu của các phần mềm ngoại.

### 5. Ý tưởng của em có thể thương mại hóa (Monetize) bằng cách nào?
Trong tương lai, hệ thống có thể tích hợp Affiliate Marketing với các siêu thị (khi xuất danh sách mua sắm nguyên liệu), hoặc ra mắt gói Premium cho phép người dùng gặp trực tuyến bác sĩ dinh dưỡng thông qua nền tảng, hoặc sử dụng hệ thống AI Vision bóc tách calo tự động qua camera.

---

## 💾 CHỦ ĐỀ 2: CÔNG NGHỆ, KIẾN TRÚC & CƠ SỞ DỮ LIỆU

### 6. Tại sao chọn PostgreSQL làm cơ sở dữ liệu thay vì MySQL hay MongoDB?
Em chọn PostgreSQL vì nó lai được ưu điểm của cả hai:
- Đảm bảo tính toàn vẹn dữ liệu quan hệ (ACID) của SQL cho các bảng User, Log.
- Cung cấp kiểu dữ liệu `JSONB` siêu mạnh để lưu trữ linh hoạt các thông số dinh dưỡng phức tạp và nguyên liệu của món ăn. Nó hỗ trợ `GIN Index` giúp quét dữ liệu JSON trực tiếp bằng SQL cực kỳ nhanh, điều mà MySQL trước đây làm rất kém.

### 7. Django (Python) đóng vai trò gì? Tại sao không dùng Node.js hay Golang?
Django là Backend Framework cung cấp sẵn cấu trúc MVT, hệ thống Admin siêu tốc và ORM mạnh mẽ. Vì dự án của em thiên về Xử lý dữ liệu (Data Analysis), Machine Learning (Naive Bayes) và AI (LLM integration) - những lĩnh vực mà Python là bá chủ hệ sinh thái. Việc dùng Django giúp mọi thứ (từ Web đến AI script) đồng nhất trong cùng một ngôn ngữ Python.

### 8. Em thiết kế các Entity (Bảng dữ liệu) cho Người dùng thế nào để cá nhân hóa hiệu quả?
Thay vì nhồi nhét, em chuẩn hóa (Normalize) thành các bảng liên kết qua `OneToOneField` và `ForeignKey`:
- `UserProfile`: Chứa chỉ số cơ thể để tính TDEE.
- `UserGoal`: Mục tiêu vận động và giảm/tăng cân.
- `UserDisease` & `UserPreference`: Các bảng này được liên kết Many-to-Many để tạo các bộ lọc bệnh lý và sở thích thức ăn. Việc tách bảng giúp dễ query và dễ mở rộng.

### 9. Lỗi N+1 Query trong ORM là gì? Em xử lý nó trong Django như thế nào?
Lỗi N+1 Query xảy ra khi ta lấy 1 danh sách N bản ghi, sau đó trong vòng lặp ta gọi tiếp N câu query để lấy dữ liệu liên kết, làm sập DB. 
Trong dự án, em sử dụng `.select_related()` (cho quan hệ 1-1, 1-N dùng SQL JOIN) và `.prefetch_related()` (cho quan hệ N-N) để gộp tất cả việc lấy dữ liệu về thành 1 hoặc 2 câu lệnh SQL duy nhất, giảm tải 90% truy vấn dư thừa.

### 10. Em có gặp vấn đề thắt cổ chai (Bottleneck) khi gọi API LLM tốn thời gian không?
Có. LLM API có thể tốn 5 giây. Em thiết kế theo kiến trúc **Graceful Fallback**: đặt Timeout cho request AI. Nếu bị quá hạn hoặc Rate Limit, hệ thống bắt lỗi (Exception) và lập tức gọi hàm truy xuất dữ liệu local DB siêu tốc để trả về kết quả dự phòng, giúp luồng (Thread) của Django không bị treo.

### 11. Các công nghệ Frontend em sử dụng là gì? Làm sao hiển thị các biểu đồ Calo?
Frontend sử dụng HTML/CSS/JS (có thể kèm Bootstrap/Tailwind). Để vẽ các biểu đồ (Dashboard) theo dõi Calories/Protein/Fat, em dùng thư viện Chart.js. Dữ liệu được tính toán tổng hợp dưới Backend Django và truyền qua API dạng JSON cho Chart.js render.

---

## 🧠 CHỦ ĐỀ 3: THUẬT TOÁN HỌC MÁY & PHÂN LOẠI (NAIVE BAYES)

### 12. Tại sao em lại tự xây dựng thuật toán Naive Bayes mà không gọi thẳng LLM cho khỏe?
Việc gọi LLM (như Gemini) cho mọi thứ tốn nhiều thời gian, tốn tiền API và dễ bị Rate Limit. Mô hình Naive Bayes đóng vai trò làm **Bộ định tuyến (Router/Intent Classifier)** siêu nhẹ. Nó giúp lọc ngay lập tức các ý định đơn giản hoặc truy vấn dữ liệu cục bộ nội bộ mà không cần đụng đến API bên ngoài.

### 13. Em hãy trình bày công thức và quá trình huấn luyện của Naive Bayes?
Mô hình hoạt động dựa trên định lý Bayes. Khi có dữ liệu là các câu Pattern (VD: "ăn gì giảm cân"), hệ thống sẽ:
1. Tokenize (Tách từ).
2. Xây dựng Vocabulary (Đếm tần suất từ khóa).
3. Tính *Prior probability* (Xác suất tiên nghiệm của ý định) và *Likelihood* (Xác suất xuất hiện của từ trong ý định đó).
Trọng số học được sẽ lưu vào 1 file JSON để Backend gọi ra suy luận cực nhanh.

### 14. Trong Naive Bayes, làm sao để tránh lỗi tràn số dưới (Underflow) khi nhân liên tục các xác suất rất nhỏ (0.00x)?
Em không nhân các xác suất trực tiếp với nhau mà chuyển sang dùng **Log-probability (Logarit cơ số e)**. Lúc này phép nhân xác suất sẽ biến thành phép cộng các Log: $\log(A \times B) = \log(A) + \log(B)$. Việc này giúp tránh bị lỗi underflow trên CPU máy tính.

### 15. Bài toán Zero-frequency: Nếu người dùng nhập từ chưa từng học thì xác suất bằng 0 và hệ thống lỗi, em giải quyết thế nào?
Em sử dụng kỹ thuật **Laplace Smoothing (Làm mịn Laplace)**. Bằng cách cộng thêm $1$ vào số lần xuất hiện của từ (Tử số) và cộng độ lớn từ vựng vào Tổng số từ (Mẫu số). Như vậy, mọi từ mới đều có xác suất $>0$, mô hình không bao giờ bị nhân với $0$.

### 16. Em làm sao để NLP xử lý được việc người dùng gõ không dấu, sai lỗi chính tả?
Trong Pipeline, em thiết kế một bộ **Text Normalizer** dùng thư viện `unicodedata`. Chuỗi sẽ bị loại bỏ hết dấu thanh (diacritics), đưa về chữ thường (lowercase) và xóa ký tự lạ. Do mô hình được train trên bộ từ không dấu này, nên dù người dùng gõ "thực đơn", "thuc don" hay "thực don" thì nó đều đưa về cùng 1 mã token để nhận diện chính xác.

---

## 🤖 CHỦ ĐỀ 4: RAG VÀ TƯƠNG TÁC LLM (GEMINI/QWEN)

### 17. Giải pháp RAG (Retrieval-Augmented Generation) hoạt động cụ thể thế nào để ngăn chặn tình trạng "bịa đặt thông tin" (Hallucination) của AI?
Cơ chế RAG gồm 2 pha:
1. **Retrieval:** Thay vì hỏi LLM "Thịt bò bao nhiêu calo", hệ thống tự chọc vào CSDL PostgreSQL nội bộ để kéo ra dữ liệu chuẩn xác $100\%$ của công thức.
2. **Augmented Generation:** Hệ thống đính kèm kết quả trên vào Prompt: *"Dựa vào dữ liệu sau [Thịt bò 250 calo], hãy lên thực đơn..."*. LLM bị ép dùng Context này nên câu trả lời tự nhiên nhưng số liệu dinh dưỡng không bao giờ bị "ảo giác" (bịa đặt).

### 18. Prompt Engineering: Cấu trúc Prompt em gửi đi cho LLM có những thành phần nào?
Prompt của em luôn chứa 3 phần:
1. **System Instruction:** Thiết lập Persona ("Bạn là chuyên gia dinh dưỡng...").
2. **Context (Ngữ cảnh RAG & User Profile):** Chứa TDEE, bệnh lý đã được ẩn danh, sở thích, và dữ liệu món ăn kéo từ DB.
3. **User Query:** Câu hỏi thật của người dùng.
Việc chia nhỏ giúp LLM hiểu ranh giới đâu là hệ thống thiết lập, đâu là câu hỏi, chống việc người dùng thao túng prompt (Prompt Injection).

### 19. Nếu cuộc hội thoại kéo dài hàng trăm câu hỏi, việc gửi lại toàn bộ ngữ cảnh sẽ làm quá tải Token. Em xử lý sao?
Em sử dụng kỹ thuật **Cửa sổ trượt (Sliding Window)** cho lịch sử hội thoại. Hệ thống chỉ bốc ra N tin nhắn gần nhất (ví dụ: 10 tin cuối) kèm theo System Context tĩnh để gửi đi. Các tin nhắn quá cũ sẽ bị cắt bỏ khỏi Prompt để tiết kiệm Token và tránh việc AI bị nhiễu thông tin cũ.

---

## 🥗 CHỦ ĐỀ 5: THUẬT TOÁN CÁ NHÂN HÓA VÀ DINH DƯỠNG

### 20. Thuật toán cá nhân hóa sử dụng cơ chế gì? Hybrid Recommender System là gì?
Thuật toán của em là Hệ gợi ý lai. Em kết hợp:
1. **Rule-based (Hard Constraints):** Lọc bỏ tức thì các món vi phạm bệnh lý hoặc ngân sách.
2. **Content-based Filtering:** Tính điểm số độ tương đồng (Jaccard similarity) giữa thuộc tính món ăn và từ khóa sở thích/mục tiêu của người dùng (Ví dụ: Thích cá hồi thì món có cá hồi + 0.5 điểm).
3. **Recency Penalty:** Nếu nhật ký ăn uống cho thấy người dùng vừa ăn món đó hôm qua, hệ thống sẽ trừ điểm để tránh lặp lại món ăn.

### 21. Chỉ số TDEE được tính bằng công thức nào?
Em dùng công thức khoa học **Mifflin-St Jeor** để tính BMR (Nam: $10 \times W + 6.25 \times H - 5 \times A + 5$, Nữ: $-161$ thay vì $+5$). Sau đó nhân với hệ số vận động để ra TDEE tổng calo tiêu hao một ngày. Đây là chuẩn y khoa đáng tin cậy nhất.

### 22. Hiện tượng Cold-Start (Khởi động lạnh) trong Recommender System là gì và em xử lý thế nào cho user mới đăng ký?
Khởi động lạnh là khi người dùng mới chưa có nhật ký ăn uống hay lượt like nào để hệ thống học. Em xử lý bằng cách ở màn hình đăng ký ban đầu (Onboarding), hệ thống bắt buộc người dùng chọn Mục tiêu (Giảm cân/Tăng cơ) và Sở thích (Đồ nướng, luộc, ăn chay). Dựa vào các từ khóa khai báo tĩnh này, Content-based Filtering sẽ có đủ điểm tựa để đưa ra gợi ý ban đầu cực tốt.

### 23. Quá trình chuẩn hóa dữ liệu thực phẩm (Data Imputation/Preprocessing) khi cào dữ liệu từ Web diễn ra thế nào?
Dữ liệu crawl thô thường thiếu chỉ số dinh dưỡng. Em viết các Scrips (Management Commands):
1. **Quy đổi chuẩn:** Đổi mọi công thức về tỉ lệ 100g.
2. **Điền khuyết (Imputation):** Nếu thực phẩm X bị thiếu Protein, hệ thống tự động tìm các thực phẩm cùng chung `Category` (Ví dụ: Thịt lợn) và lấy giá trị trung bình cộng đập vào X. Đảm bảo lúc AI tính toán không bị sập do trường dữ liệu bị NULL.

---

## 🛡️ CHỦ ĐỀ 6: BẢO MẬT, TỐI ƯU VÀ TRIỂN KHAI

### 24. Nguyên tắc "Quyền tối thiểu" (Least Privilege) và "Ẩn danh hóa" (Pseudonymization) khi gọi Gemini API được áp dụng ra sao?
Em tuyệt đối KHÔNG đưa thông tin PII (Personally Identifiable Information) như Họ Tên, Email hay ID vào Prompt. Em chỉ ghép hồ sơ ẩn danh dạng: *"Người dùng 25 tuổi, Nam, bệnh: Tiểu đường"*. Hơn nữa, nếu intent câu hỏi là hỏi "cách nấu cơm", hệ thống sẽ cắt gỡ luôn cả phần tiểu đường ra khỏi Prompt vì nó không cần thiết, bảo mật tuyệt đối cho dữ liệu y khoa của người dùng.

### 25. Em có sử dụng Caching không? Cơ chế Cache Invalidation (Làm mới cache) của hệ thống hoạt động thế nào?
Có. Em dùng Database (hoặc Redis) để Cache câu trả lời của LLM cho các câu hỏi trùng lặp. 
**Vấn đề Invalidation:** Nếu người dùng đổi bệnh nền từ "Bình thường" sang "Mỡ máu", các cache cũ không được xài lại nữa. Giải pháp của em là sinh ra **Cache Key** bằng hàm băm (MD5) của chuỗi `[Câu hỏi] + [Hồ sơ sức khỏe hiện tại]`. Nếu hồ sơ thay đổi, MD5 Key thay đổi, sinh ra Cache Miss và bắt buộc hệ thống phải lấy dữ liệu thực đơn mới.

### 26. Quá trình cào dữ liệu (Crawling) siêu thị em gặp khó khăn gì với trang web động?
Các siêu thị như WinMart xài Javascript để render dữ liệu và chống Bot. 
Cách giải quyết của em là không dùng thư viện đọc HTML tĩnh bình thường, mà em sử dụng công cụ Network Sniffing để tìm đường link API (JSON) ngầm của website, hoặc dùng Headless Browser giả lập thao tác lăn chuột và xoay vòng User-Agent để lách Anti-Bot.

### 27. Nếu em phải Deploy (Triển khai) hệ thống này lên môi trường thực tế (Production), em sẽ dùng cấu trúc hạ tầng nào?
Em sẽ "Dockerize" (Đóng gói Docker) dự án thành các container độc lập:
1. Container Django (Backend API).
2. Container PostgreSQL (Database).
3. Container Redis (Caching).
Và sử dụng Nginx làm Reverse Proxy, kết hợp Gunicorn để chạy multi-worker cho Django, đảm bảo khả năng chịu tải hàng ngàn request đồng thời.

### 28. Quản trị viên (Admin) làm sao để thay đổi các Intent của AI hoặc dạy AI thêm từ mới mà không cần can thiệp vào Source Code?
Em đã đưa hoàn toàn cấu trúc `Intent` và `Pattern` thành các bảng trong CSDL thay vì code cứng vào file Python. Admin chỉ cần đăng nhập giao diện Django Admin portal (GUI), thêm câu mẫu mới (Ví dụ: "Tôi bị béo phì"). Sau đó bấm nút trigger trong Dashboard, hệ thống tự động chạy lại thuật toán huấn luyện Naive Bayes ở Background (nhờ luồng xử lý bất đồng bộ) và update JSON Model ngay lập tức.

### 29. Kế hoạch phát triển hệ thống nếu có thêm 6 tháng nữa?
1. Nâng cấp bộ phân loại Intent từ Naive Bayes sang dùng Embedding Vector thu nhỏ (như mô hình PhoBERT) để bắt được độ tương đồng ngữ nghĩa sâu hơn.
2. Áp dụng AI Vision bóc tách hình ảnh: Chụp mâm cơm ra calo.
3. Xuất "Giỏ hàng nguyên liệu" tích hợp API bên thứ ba để ship đồ ăn tận nhà.
4. Tối ưu hóa Database với `pgvector` để đẩy nhanh quá trình query tương đồng Vector RAG trong DB nội bộ thay vì tính điểm Cosine bằng Python.
