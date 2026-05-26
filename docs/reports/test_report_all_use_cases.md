# BÁO CÁO KIỂM THỬ CHUẨN - TOÀN BỘ USE CASE

**Dự án:** Smart Home Chef (AI Agent)  
**Loại tài liệu:** Báo cáo kiểm thử chuẩn theo use case  
**Phạm vi:** Toàn bộ use case được liệt kê trong yêu cầu của người dùng  
**Nguyên tắc ghi nhận:**
- **PASS**: Thực tế trùng với mong đợi.
- **FAIL**: Thực tế khác mong đợi, kèm ID bug tương ứng.
- **BLOCK**: Không thể thực hiện do lỗi/phụ thuộc/dữ liệu chặn đường.

**Lưu ý về đánh số:** Danh sách gốc của người dùng bỏ qua các số 22, 23, 24. Báo cáo này giữ nguyên thứ tự các use case được cung cấp.

---

## 1. Tóm tắt kết quả

| Chỉ số | Số lượng |
|---|---:|
| Tổng use case | 40 |
| PASS | 4 |
| FAIL | 9 |
| BLOCK | 27 |

---

## 2. Chi tiết kiểm thử

### 2.1. Xác thực tài khoản

| Mã kịch bản (ID) | UC trong yêu cầu | Dữ liệu đầu vào (Input) | Mô tả hành động của người dùng | Kết quả mong đợi (Expected Output) | Kết quả thực tế (Actual Output) | Trạng thái | Bug ID |
|---|---|---|---|---|---|---|---|
| TC-001 | UC-01 | username: `qa_user_01`; password: `Qa@123456`; email: `qa_user_01@example.com` | Nhập thông tin và click **Đăng ký** | Tạo tài khoản mới, hiển thị thông báo thành công, chuyển sang trang đăng nhập/bảng điều khiển | Đúng như mong đợi | PASS | - |
| TC-002 | UC-02 | username: `qa_user_01`; password: `Qa@123456` | Nhập tài khoản và click **Đăng nhập** | Xác thực thành công, tạo phiên đăng nhập, chuyển tới trang chính | Đúng như mong đợi | PASS | - |
| TC-003 | UC-03 | Đang đăng nhập bằng `qa_user_01` | Click **Đăng xuất** | Hệ thống xóa phiên làm việc, chuyển về trang đăng nhập/home | Đúng như mong đợi | PASS | - |
| TC-004 | UC-04 | admin: `admin`; password: `Admin@123456` | Truy cập trang quản trị và click **Đăng nhập** | Xác thực quyền admin, chuyển vào khu vực quản trị | Đúng như mong đợi | PASS | - |

### 2.2. Dinh dưỡng và thực phẩm

| Mã kịch bản (ID) | UC trong yêu cầu | Dữ liệu đầu vào (Input) | Mô tả hành động của người dùng | Kết quả mong đợi (Expected Output) | Kết quả thực tế (Actual Output) | Trạng thái | Bug ID |
|---|---|---|---|---|---|---|---|
| TC-005 | UC-05 | food: `ức gà`; quantity: `100g`; meal_type: `trưa`; date: `2026-05-19` | Chọn thực phẩm, nhập khẩu phần, click **Thêm nhật ký ăn uống** | Tạo bản ghi NutritionLog và cập nhật chỉ số dinh dưỡng | HTTP 404, không tìm thấy endpoint ghi nhật ký ăn uống | FAIL | BUG-NUT-001 |
| TC-006 | UC-06 | keyword: `gạo` | Nhập từ khóa vào ô tìm kiếm và click **Tìm kiếm** | Hiển thị danh sách thực phẩm phù hợp từ DB/API | HTTP 404, không tìm thấy endpoint tìm kiếm thực phẩm | FAIL | BUG-NUT-002 |
| TC-007 | UC-07 | food_id: `101` | Click vào một thực phẩm trong danh sách để xem chi tiết | Hiển thị trang/khung chi tiết với kcal, protein, carb, fat | HTTP 404, không tìm thấy endpoint chi tiết thực phẩm | FAIL | BUG-NUT-003 |
| TC-008 | UC-08 | quantity: `150g`; nutrition/100g: `protein=20`, `carb=0`, `fat=5`, `kcal=120` | Nhập số lượng và click **Tính lượng dinh dưỡng nạp vào** | Hệ thống tính đúng macro/kcal theo khẩu phần | HTTP 404, không tìm thấy endpoint tính dinh dưỡng | FAIL | BUG-NUT-004 |
| TC-009 | UC-09 | khoảng thời gian: `hôm nay` | Mở màn hình nhật ký dinh dưỡng | Hiển thị danh sách nhật ký dinh dưỡng của người dùng | Chưa thể thực hiện do chưa có dữ liệu nhật ký hợp lệ để đối soát | BLOCK | BUG-NUT-001 |
| TC-010 | UC-10 | log_id: `501`; quantity mới: `120g`; meal_type: `tối`; date: `2026-05-19` | Chọn bản ghi và click **Cập nhật** | Bản ghi được cập nhật và lưu vào DB | Chưa thể thực hiện do luồng thêm nhật ký bị chặn ở TC-005 | BLOCK | BUG-NUT-001 |
| TC-011 | UC-11 | log_id: `501` | Chọn bản ghi và click **Xóa** | Bản ghi bị xóa khỏi DB và biến mất khỏi danh sách | Chưa thể thực hiện do chưa có bản ghi nhật ký hợp lệ để xóa | BLOCK | BUG-NUT-001 |
| TC-012 | UC-12 | không có đầu vào | Mở dashboard hằng ngày | Hiển thị thẻ kcal/protein/carb/fat, trạng thái thiếu/đủ/vượt | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-013 | UC-13 | không có đầu vào; dữ liệu so sánh lấy từ dashboard | Mở mục so sánh dinh dưỡng | Hiển thị so sánh hôm nay với hôm qua/tuần trước | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-014 | UC-14 | nutrition summary trong ngày | Mở khu vực gợi ý dinh dưỡng | Hiển thị gợi ý dinh dưỡng phù hợp từ hệ thống | HTTP 404, không tìm thấy endpoint gợi ý dinh dưỡng | FAIL | BUG-NUT-005 |

### 2.3. Thực đơn

| Mã kịch bản (ID) | UC trong yêu cầu | Dữ liệu đầu vào (Input) | Mô tả hành động của người dùng | Kết quả mong đợi (Expected Output) | Kết quả thực tế (Actual Output) | Trạng thái | Bug ID |
|---|---|---|---|---|---|---|---|
| TC-015 | UC-15 | ngày: `2026-05-19`; mục tiêu macro: `auto`; món ăn: `ức gà`, `cơm`, `rau luộc` | Nhập dữ liệu và click **Tạo thực đơn** | Tạo mới meal plan và lưu vào DB | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-016 | UC-16 | khoảng ngày: `2026-05-19` đến `2026-05-25` | Mở màn hình xem thực đơn | Hiển thị danh sách thực đơn theo khoảng ngày | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-017 | UC-17 | meal_plan_id: `2001`; nội dung cần đổi | Chọn thực đơn và click **Cập nhật** | Dữ liệu thực đơn được cập nhật thành công | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-018 | UC-18 | meal_plan_id: `2001`; food_id: `101`; quantity: `100g` | Chọn thực đơn, thêm món và click **Lưu** | Món mới được thêm vào thực đơn và hiển thị trong danh sách món | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-019 | UC-19 | meal_plan_item_id: `3001`; serving: `150g`; meal_type: `trưa` | Sửa khẩu phần/loại bữa và click **Lưu** | Bản ghi món trong thực đơn được cập nhật | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-020 | UC-20 | meal_plan_id: `2001` hoặc meal_plan_item_id: `3001` | Click **Xóa thực đơn** hoặc **Xóa món khỏi thực đơn** | Dữ liệu được xóa khỏi DB, giao diện cập nhật tương ứng | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |

### 2.4. Chat và phân tích hành vi

| Mã kịch bản (ID) | UC trong yêu cầu | Dữ liệu đầu vào (Input) | Mô tả hành động của người dùng | Kết quả mong đợi (Expected Output) | Kết quả thực tế (Actual Output) | Trạng thái | Bug ID |
|---|---|---|---|---|---|---|---|
| TC-021 | UC-21 | message: `Hôm nay tôi ăn bao nhiêu protein?` | Nhập tin nhắn và click **Gửi** | Tạo chat message, sinh phản hồi từ hệ thống/AI | HTTP 404, không tìm thấy endpoint gửi tin nhắn chat | FAIL | BUG-CHAT-001 |
| TC-022 | UC-25 | không có đầu vào; session chat hiện tại | Mở màn hình lịch sử chat | Hiển thị danh sách tin nhắn theo phiên chat | HTTP 404, không tìm thấy endpoint lịch sử chat | FAIL | BUG-CHAT-002 |
| TC-023 | UC-26 | chat_session_id: `7001` | Click **Xóa phiên chat / tin nhắn** | Phiên chat hoặc tin nhắn bị xóa, giao diện tạo phiên mới | HTTP 404, không tìm thấy endpoint xóa phiên chat/tin nhắn | FAIL | BUG-CHAT-003 |
| TC-024 | UC-27 | message + dữ liệu dinh dưỡng 7 ngày gần nhất | Gửi tin nhắn và chờ hệ thống phân tích | Trả về nhận xét về hành vi sức khỏe, cảnh báo hoặc khuyến nghị | HTTP 404, không tìm thấy endpoint phân tích hành vi sức khỏe | FAIL | BUG-AI-001 |

### 2.5. Hồ sơ và tài khoản

| Mã kịch bản (ID) | UC trong yêu cầu | Dữ liệu đầu vào (Input) | Mô tả hành động của người dùng | Kết quả mong đợi (Expected Output) | Kết quả thực tế (Actual Output) | Trạng thái | Bug ID |
|---|---|---|---|---|---|---|---|
| TC-025 | UC-28 | không có đầu vào | Mở trang hồ sơ cá nhân | Hiển thị thông tin hồ sơ của người dùng | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-026 | UC-29 | age: `28`; weight: `62`; goal: `giảm mỡ`; note: `không ăn cay` | Chỉnh sửa thông tin và click **Cập nhật hồ sơ** | Thông tin được lưu thành công vào DB | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-027 | UC-30 | age, weight, height, mục tiêu sức khỏe | Chọn chức năng tính mục tiêu dinh dưỡng | Hệ thống tính target kcal/macro phù hợp | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-028 | UC-31 | xác nhận xóa tài khoản; mật khẩu hiện tại: `Qa@123456` | Chọn **Xóa tài khoản** và xác nhận | Tài khoản bị xóa/vô hiệu hóa, phiên đăng nhập kết thúc | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |

### 2.6. Nhập dữ liệu và quản trị thực phẩm

| Mã kịch bản (ID) | UC trong yêu cầu | Dữ liệu đầu vào (Input) | Mô tả hành động của người dùng | Kết quả mong đợi (Expected Output) | Kết quả thực tế (Actual Output) | Trạng thái | Bug ID |
|---|---|---|---|---|---|---|---|
| TC-029 | UC-32 | file import: `foods_seed.xlsx` hoặc dữ liệu nguồn tương đương | Upload file hoặc chạy chức năng nhập dữ liệu | Dữ liệu được import thành công vào DB | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-030 | UC-33 | tên thực phẩm: `Yến mạch`; đơn vị: `100g`; kcal: `389` | Thêm mới thực phẩm và click **Lưu** | Bản ghi thực phẩm mới được tạo | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-031 | UC-34 | không có đầu vào; danh sách thực phẩm hiện có | Mở danh sách thực phẩm | Hiển thị danh sách và/hoặc chi tiết thực phẩm | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-032 | UC-35 | food_id: `101`; tên mới: `Ức gà không da` | Mở chi tiết thực phẩm và click **Sửa** | Thông tin thực phẩm được cập nhật | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-033 | UC-36 | food_id: `101` | Chọn thực phẩm và click **Xóa** | Thực phẩm bị xóa khỏi DB và biến mất khỏi danh sách | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-034 | UC-37 | dữ liệu trùng/lỗi: `food_name`, `barcode`, `legacy_ids` | Chạy chức năng dọn dữ liệu | Hệ thống loại bỏ bản ghi trùng/lỗi và ghi nhận log | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |

### 2.7. Intent / Pattern

| Mã kịch bản (ID) | UC trong yêu cầu | Dữ liệu đầu vào (Input) | Mô tả hành động của người dùng | Kết quả mong đợi (Expected Output) | Kết quả thực tế (Actual Output) | Trạng thái | Bug ID |
|---|---|---|---|---|---|---|---|
| TC-035 | UC-38 | intent name: `nutrition_advice`; pattern: `ăn bao nhiêu protein`; response template tương ứng | Thêm intent/pattern và click **Lưu** | Intent/pattern mới được lưu và sẵn sàng dùng | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-036 | UC-39 | intent_id: `intent-01`; pattern mới: `cần ăn gì để tăng cơ` | Chọn intent/pattern, sửa nội dung và lưu | Thông tin intent/pattern được cập nhật | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-037 | UC-40 | intent_id: `intent-01` | Chọn intent/pattern và click **Xóa** | Intent/pattern bị xóa khỏi hệ thống | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |

### 2.8. Người dùng hệ thống

| Mã kịch bản (ID) | UC trong yêu cầu | Dữ liệu đầu vào (Input) | Mô tả hành động của người dùng | Kết quả mong đợi (Expected Output) | Kết quả thực tế (Actual Output) | Trạng thái | Bug ID |
|---|---|---|---|---|---|---|---|
| TC-038 | UC-41 | không có đầu vào; bộ lọc danh sách người dùng | Mở danh sách/chi tiết người dùng | Hiển thị danh sách tài khoản và thông tin chi tiết | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-039 | UC-42 | user_id: `15`; role mới: `admin`; status: `active` | Cập nhật vai trò hoặc trạng thái người dùng và lưu | Vai trò/trạng thái được cập nhật thành công | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |
| TC-040 | UC-43 | user_id: `15`; hành động: `disable` hoặc `delete` | Chọn **Xóa/vô hiệu hóa người dùng** và xác nhận | Người dùng bị vô hiệu hóa/xóa, hệ thống cập nhật đúng trạng thái | Chưa thực thi trong đợt kiểm thử hiện tại | BLOCK | - |

---

## 3. Danh sách bug liên quan

| Bug ID | Mô tả |
|---|---|
| BUG-NUT-001 | Thiếu endpoint ghi nhật ký ăn uống, ảnh hưởng thêm/xem/sửa/xóa nhật ký. |
| BUG-NUT-002 | Thiếu endpoint tìm kiếm thực phẩm. |
| BUG-NUT-003 | Thiếu endpoint xem chi tiết thực phẩm. |
| BUG-NUT-004 | Thiếu endpoint tính lượng dinh dưỡng nạp vào. |
| BUG-NUT-005 | Thiếu endpoint nhận gợi ý dinh dưỡng. |
| BUG-CHAT-001 | Thiếu endpoint gửi tin nhắn chat. |
| BUG-CHAT-002 | Thiếu endpoint xem lịch sử chat. |
| BUG-CHAT-003 | Thiếu endpoint xóa phiên chat/tin nhắn. |
| BUG-AI-001 | Thiếu endpoint phân tích hành vi sức khỏe. |

---

## 4. Kết luận

Báo cáo này đã chuẩn hóa toàn bộ use case được cung cấp theo đúng 4 trường bắt buộc: dữ liệu đầu vào, mô tả hành động, kết quả mong đợi, kết quả thực tế, kèm trạng thái PASS/FAIL/BLOCK. Nhóm xác thực hiện đang PASS; nhóm nutrition và chat có các lỗi endpoint rõ ràng; phần còn lại được ghi BLOCK vì chưa có bằng chứng thực thi trong workspace hiện tại.
