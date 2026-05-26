# ĐẶC TẢ USE CASE HỆ THỐNG - Django-Json-Data

**Phiên bản:** 1.0
**Ngày cập nhật:** May 16, 2026
**Hệ thống:** Django-Json-Data

---

## 1. Giới thiệu

Tài liệu này mô tả các use case theo sơ đồ chức năng đã định nghĩa cho hệ thống Django-Json-Data. Mỗi use case được trình bày theo mẫu: mục tiêu, tác nhân, tiền điều kiện, hậu điều kiện, CRUD, luồng chính và luồng thay thế.

## 2. Quy ước

- **Người dùng:** người dùng đã đăng nhập hoặc khách truy cập.
- **Quản trị viên:** người dùng có quyền admin.
- **Hệ thống:** ứng dụng Django và các dịch vụ liên quan.
- **Phiên chat:** session chat hoặc phiên người dùng.
- **CRUD:** Create, Read, Update, Delete.

---

## 3. Use case chi tiết

### 1.1 Đăng ký tài khoản

**Mục tiêu:** Tạo mới tài khoản người dùng và bắt đầu phiên xác thực.

**Tác nhân:** Khách truy cập.

**Tiền điều kiện:** Người dùng chưa có tài khoản hợp lệ.

**Hậu điều kiện:** Tài khoản được tạo, người dùng có thể đăng nhập.

**CRUD:** Create.

**Luồng chính:**
1. Người dùng mở trang đăng ký.
2. Hệ thống hiển thị giao diện đăng ký với form nhập tên, email, mật khẩu và các trường bắt buộc.
3. Người dùng nhập tên, email, mật khẩu và thông tin bắt buộc.
4. Người dùng gửi biểu mẫu đăng ký.
5. Hệ thống xác thực cấu trúc dữ liệu và kiểm tra các trường bắt buộc.
6. Hệ thống kiểm tra trùng email/tên đăng nhập.
7. Hệ thống tạo tài khoản và hồ sơ mặc định.
8. Hệ thống trả về thông báo đăng ký thành công.

**Luồng thay thế:**
4.1. Nếu thiếu dữ liệu bắt buộc hoặc dữ liệu sai định dạng, hệ thống hiển thị lỗi và yêu cầu người dùng sửa lại.
5.1. Nếu email hoặc tên đăng nhập đã tồn tại, hệ thống thông báo trùng lặp; người dùng cung cấp giá trị khác.
4.2. Nếu mật khẩu không đạt chính sách, hệ thống yêu cầu người dùng nhập lại mật khẩu hợp lệ.

### 1.2 Đăng nhập

**Mục tiêu:** Xác thực người dùng và thiết lập phiên làm việc.

**Tác nhân:** Khách truy cập, người dùng đã đăng ký.

**Tiền điều kiện:** Tài khoản tồn tại và chưa bị khóa.

**Hậu điều kiện:** Phiên đăng nhập được tạo, quyền truy cập riêng tư được cấp.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng mở trang đăng nhập.
2. Hệ thống hiển thị giao diện đăng nhập với form tên đăng nhập/email và mật khẩu.
3. Người dùng nhập tên đăng nhập/email và mật khẩu.
4. Người dùng gửi yêu cầu đăng nhập.
5. Hệ thống xác thực thông tin đầu vào.
6. Hệ thống kiểm tra tài khoản tồn tại và mật khẩu chính xác.
7. Nếu hợp lệ, hệ thống tạo session và chuyển người dùng đến dashboard.

**Luồng thay thế:**
4.1. Nếu thông tin đăng nhập thiếu hoặc sai định dạng, hệ thống hiển thị lỗi; người dùng sửa lại.
5.1. Nếu tài khoản không tồn tại, hệ thống thông báo; người dùng kiểm tra lại thông tin hoặc đăng ký.
5.2. Nếu mật khẩu sai, hệ thống hiển thị lỗi; người dùng nhập lại.
5.3. Nếu tài khoản bị khóa, hệ thống thông báo hạn chế.
5.4. Nếu cần xác thực hai yếu tố, hệ thống yêu cầu mã OTP; người dùng nhập mã để tiếp tục.

### 1.3 Đăng xuất

**Mục tiêu:** Kết thúc phiên làm việc người dùng.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Người dùng đang đăng nhập.

**Hậu điều kiện:** Session bị huỷ, người dùng trở về trạng thái chưa đăng nhập.

**CRUD:** Delete (session).

**Luồng chính:**
1. Người dùng chọn chức năng đăng xuất từ giao diện điều hướng hoặc menu người dùng.
2. Hệ thống hiển thị thông báo xác nhận nếu cần và sau đó huỷ session và cookie phiên làm việc.
3. Hệ thống điều hướng người dùng về trang công khai.

**Luồng thay thế:**
2.1. Nếu session đã hết hạn, hệ thống vẫn điều hướng về trang công khai mà không báo lỗi.

### 1.4 Đăng nhập quản trị

**Mục tiêu:** Cấp quyền quản trị cho người dùng admin.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Tài khoản tồn tại và có quyền admin.

**Hậu điều kiện:** Phiên admin được thiết lập và quyền quản trị được cấp.

**CRUD:** Read.

**Luồng chính:**
1. Admin mở trang đăng nhập quản trị.
2. Admin nhập tên đăng nhập và mật khẩu.
3. Hệ thống xác thực thông tin và kiểm tra quyền admin.
4. Nếu hợp lệ, hệ thống tạo phiên admin và chuyển đến dashboard quản trị.

**Luồng thay thế:**
3.1. Nếu tài khoản không có quyền admin, hệ thống từ chối truy cập và hiển thị cảnh báo.
3.2. Nếu thông tin sai, hệ thống hiển thị lỗi.

### 2.1 Thêm nhật ký ăn uống

**Mục tiêu:** Ghi nhận một phần ăn vào nhật ký dinh dưỡng.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Người dùng đã đăng nhập và hồ sơ dinh dưỡng tồn tại.

**Hậu điều kiện:** Bản ghi mới được lưu trong nhật ký dinh dưỡng.

**CRUD:** Create.

**Luồng chính:**
1. Người dùng mở trang thêm nhật ký ăn uống.
2. Hệ thống hiển thị giao diện thêm nhật ký với khu vực tìm kiếm thực phẩm và danh sách lựa chọn.
3. Người dùng chuyển sang chức năng tìm kiếm thực phẩm nếu cần.
4. Người dùng nhập từ khóa tìm kiếm.
5. Hệ thống trả về danh sách thực phẩm phù hợp.
6. Người dùng chọn thực phẩm.
7. Hệ thống hiển thị chi tiết dinh dưỡng và form nhập khẩu phần.
8. Người dùng nhập lượng và xác nhận khẩu phần.
9. Hệ thống lưu bản ghi nhật ký và cập nhật tổng dinh dưỡng.

**Luồng thay thế:**
4.1. Nếu không tìm thấy thực phẩm, hệ thống hiển thị gợi ý; người dùng chọn gợi ý hoặc điều chỉnh từ kho dữ liệu.
7.1. Nếu khẩu phần không hợp lệ, hệ thống thông báo lỗi; người dùng sửa lại khẩu phần.

#### 2.1.1 Tìm kiếm thực phẩm

**Mục tiêu:** Tìm thực phẩm phù hợp để thêm vào nhật ký.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Người dùng đang ở chức năng thêm nhật ký.

**Hậu điều kiện:** Danh sách thực phẩm phù hợp được trả về.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng mở chức năng tìm kiếm thực phẩm trên giao diện thêm nhật ký.
2. Hệ thống hiển thị ô tìm kiếm và vùng kết quả trống.
3. Người dùng nhập tên hoặc thông tin thực phẩm.
4. Hệ thống tra cứu dữ liệu thực phẩm.
5. Hệ thống trả về danh sách kết quả phù hợp.

**Luồng thay thế:**
4.1. Nếu không có kết quả, hệ thống hiển thị gợi ý thay thế.

#### 2.1.2 Xem chi tiết thực phẩm

**Mục tiêu:** Xem thông tin dinh dưỡng và mô tả thực phẩm.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Người dùng đã chọn một thực phẩm từ kết quả tìm kiếm.

**Hậu điều kiện:** Người dùng có đủ thông tin để quyết định khẩu phần.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng chọn thực phẩm từ danh sách kết quả.
2. Hệ thống hiển thị chi tiết dinh dưỡng, thành phần và đơn vị đo trên cùng một trang hoặc panel.
3. Người dùng xác nhận hoặc quay lại tìm kiếm.

**Luồng thay thế:**
2.1. Nếu dữ liệu thực phẩm không đầy đủ, hệ thống cảnh báo và hiển thị thông tin tối thiểu.

#### 2.1.3 Tính lượng dinh dưỡng nạp vào

**Mục tiêu:** Tính toán dinh dưỡng dựa trên khẩu phần người dùng chọn.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Người dùng đã chọn thực phẩm và nhập lượng.

**Hậu điều kiện:** Lượng calo, đạm, béo, tinh bột và vitamin được hiển thị.

**CRUD:** Read / Update (trên bản ghi tạm thời).

**Luồng chính:**
1. Người dùng nhập khẩu phần hoặc lượng trên giao diện chi tiết thực phẩm.
2. Hệ thống tính toán dinh dưỡng theo tỷ lệ đơn vị và hiển thị kết quả ngay lập tức.
3. Hệ thống hiển thị tổng dinh dưỡng của bản ghi.
4. Người dùng điều chỉnh nếu cần và xác nhận.
5. Hệ thống cập nhật bản ghi tạm thời.

**Luồng thay thế:**
2.1. Nếu lượng nhập vào không hợp lệ, hệ thống thông báo lỗi; người dùng sửa lại.
2.2. Nếu dữ liệu dinh dưỡng của thực phẩm thiếu, hệ thống hiển thị cảnh báo và ghi chú ước lượng.

### 2.2 Xem nhật ký dinh dưỡng

**Mục tiêu:** Tra cứu lịch sử ăn uống và tổng quan dinh dưỡng.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Người dùng đã có ít nhất một bản ghi nhật ký, hoặc có quyền xem trang.

**Hậu điều kiện:** Thông tin nhật ký được hiển thị, không thay đổi dữ liệu.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng mở trang nhật ký dinh dưỡng.
2. Hệ thống hiển thị giao diện nhật ký với điều hướng theo ngày/tuần/tháng.
3. Hệ thống truy vấn nhật ký theo ngày/tuần/tháng.
4. Hệ thống hiển thị danh sách bản ghi và tổng dinh dưỡng.
5. Người dùng xem chi tiết và chuyển đổi giữa các khoảng thời gian.

**Luồng thay thế:**
2.1. Nếu không có bản ghi, hệ thống hiển thị trạng thái trống và hướng dẫn người dùng tạo bản ghi mới.

### 2.3 Cập nhật nhật ký dinh dưỡng

**Mục tiêu:** Sửa nội dung bản ghi ăn uống đã lưu.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Bản ghi cần sửa tồn tại và thuộc người dùng.

**Hậu điều kiện:** Bản ghi được cập nhật.

**CRUD:** Update.

**Luồng chính:**
1. Người dùng chọn bản ghi cần chỉnh sửa.
2. Hệ thống hiển thị form chỉnh sửa.
3. Người dùng sửa thực phẩm, lượng hoặc ghi chú.
4. Người dùng lưu thay đổi.
5. Hệ thống kiểm tra và cập nhật bản ghi.
6. Hệ thống hiển thị thông báo thành công.

**Luồng thay thế:**
3.1. Nếu bản ghi không tồn tại, hệ thống thông báo lỗi.
5.1. Nếu dữ liệu cập nhật không hợp lệ, hệ thống hiển thị cảnh báo và yêu cầu người dùng sửa lại.

### 2.4 Xóa bản ghi nhật ký dinh dưỡng

**Mục tiêu:** Xóa một bản ghi ăn uống không còn cần thiết.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Bản ghi tồn tại và thuộc về người dùng.

**Hậu điều kiện:** Bản ghi bị xóa và tổng dinh dưỡng cập nhật.

**CRUD:** Delete.

**Luồng chính:**
1. Người dùng chọn xóa bản ghi.
2. Hệ thống yêu cầu xác nhận.
3. Người dùng xác nhận xóa.
4. Hệ thống xóa bản ghi và cập nhật tổng dinh dưỡng.
5. Hệ thống hiển thị thông báo thành công.

**Luồng thay thế:**
2.1. Nếu người dùng hủy xác nhận, hệ thống giữ nguyên bản ghi.
4.1. Nếu bản ghi đã bị xóa trước đó, hệ thống thông báo không tìm thấy.

### 3.1 Xem bảng điều khiển hằng ngày

**Mục tiêu:** Người dùng có hồ sơ và dữ liệu nhật ký.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Người dùng có hồ sơ và dữ liệu nhật ký.

**Hậu điều kiện:** Không thay đổi dữ liệu, chỉ cung cấp thông tin.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng mở dashboard.
2. Hệ thống hiển thị giao diện bảng điều khiển với các khu vực tóm tắt dinh dưỡng.
3. Hệ thống truy vấn dữ liệu dinh dưỡng theo ngày.
4. Hệ thống tính toán tổng calo, tỷ lệ macro và trạng thái mục tiêu.
5. Hệ thống hiển thị bảng điều khiển.
6. Người dùng xem và đánh giá kết quả.

**Luồng thay thế:**
2.1. Nếu thiếu dữ liệu, hệ thống hiển thị cảnh báo và gợi ý người dùng thêm nhật ký.

### 3.2 So sánh dinh dưỡng

**Mục tiêu:** So sánh dinh dưỡng giữa các ngày, bữa hoặc mục tiêu.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Có dữ liệu nhật ký đủ cho mục so sánh.

**Hậu điều kiện:** Hiển thị biểu đồ/so sánh.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng chọn khoảng thời gian hoặc tiêu chí so sánh.
2. Hệ thống truy vấn dữ liệu phù hợp.
3. Hệ thống hiển thị biểu đồ và số liệu so sánh.
4. Người dùng đọc và so sánh kết quả.

**Luồng thay thế:**
2.1. Nếu dữ liệu hạn chế, hệ thống hiển thị cảnh báo và chỉ so sánh những ngày có dữ liệu.

### 3.3 Nhận gợi ý dinh dưỡng

**Mục tiêu:** Đề xuất điều chỉnh dinh dưỡng dựa trên mục tiêu và nhật ký.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Hồ sơ và nhật ký hiện tại tồn tại.

**Hậu điều kiện:** Hiển thị gợi ý phù hợp.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng mở phần gợi ý dinh dưỡng.
2. Hệ thống tổng hợp hồ sơ và nhật ký hiện có.
3. Hệ thống phân tích và đề xuất điều chỉnh khẩu phần, thực phẩm hoặc cân bằng macro.
4. Hệ thống hiển thị gợi ý cho người dùng.

**Luồng thay thế:**
2.1. Nếu hồ sơ không đầy đủ, hệ thống yêu cầu người dùng cập nhật mục tiêu hoặc chỉ số cơ thể.

### 4.1 Tạo thực đơn

**Mục tiêu:** Sinh hoặc tạo thủ công thực đơn theo nhu cầu người dùng.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Người dùng đã có hồ sơ và mục tiêu dinh dưỡng.

**Hậu điều kiện:** Thực đơn mới được tạo và lưu trữ.

**CRUD:** Create.

**Luồng chính:**
1. Người dùng mở chức năng lập thực đơn.
2. Hệ thống hiển thị giao diện lập thực đơn với tùy chọn tạo thủ công hoặc tạo bằng AI.
3. Người dùng chọn tạo thủ công hoặc tạo bằng AI.
4. Hệ thống chuẩn bị giao diện tương ứng.
5. Người dùng xác nhận lưu thực đơn.
6. Hệ thống lưu thực đơn.

**Luồng thay thế:**
2.1. Nếu dữ liệu mục tiêu thiếu, hệ thống yêu cầu người dùng cập nhật hồ sơ trước.

#### 4.1.1 Tạo từ nhập liệu người dùng

**Mục tiêu:** Cho phép người dùng xây dựng thực đơn bằng cách chọn món và khẩu phần.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Có danh sách món và thông tin dinh dưỡng.

**Hậu điều kiện:** Thực đơn được lưu với các món đã chọn.

**CRUD:** Create.

**Luồng chính:**
1. Người dùng chọn ngày và loại bữa.
2. Người dùng tìm kiếm hoặc chọn món.
3. Người dùng nhập khẩu phần và điều chỉnh nếu cần.
4. Người dùng lưu thực đơn.
5. Hệ thống xác thực và lưu dữ liệu.

**Luồng thay thế:**
2.1. Nếu món không đủ dữ liệu, hệ thống cảnh báo và đề xuất thay thế.

#### 4.1.2 Tạo tự động bằng AI (Gemini/DB)

**Mục tiêu:** Sinh thực đơn tự động dựa trên mục tiêu và dữ liệu người dùng.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Hồ sơ và mục tiêu dinh dưỡng đầy đủ.

**Hậu điều kiện:** Thực đơn tự động được tạo và hiển thị cho người dùng.

**CRUD:** Create.

**Luồng chính:**
1. Người dùng chọn tạo tự động.
2. Hệ thống hiển thị trạng thái chờ, các thông số mục tiêu và nút gửi.
3. Người dùng xác nhận yêu cầu tạo tự động.
4. Hệ thống gửi yêu cầu đến dịch vụ AI hoặc cơ sở dữ liệu nội bộ.
5. Hệ thống nhận kết quả thực đơn.
6. Hệ thống hiển thị thực đơn cho người dùng.
7. Người dùng xác nhận và lưu.
8. Hệ thống lưu thực đơn.

**Luồng thay thế:**
3.1. Nếu API AI lỗi, hệ thống hiển thị thông báo và đề xuất tạo bằng tay.
4.1. Nếu kết quả không phù hợp, người dùng chỉnh sửa và lưu lại.

### 4.2 Xem thực đơn (lịch/chi tiết ngày)

**Mục tiêu:** Hiển thị thực đơn theo tuần/ngày và chi tiết từng bữa.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Có thực đơn đã lưu.

**Hậu điều kiện:** Không thay đổi dữ liệu.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng mở trang xem thực đơn.
2. Hệ thống hiển thị giao diện lịch thực đơn với ngày, tuần và các ô bữa ăn.
3. Hệ thống truy vấn thực đơn theo lịch.
4. Hệ thống hiển thị lịch thực đơn theo ngày/tuần.
5. Người dùng chọn ngày để xem chi tiết từng bữa.

**Luồng thay thế:**
2.1. Nếu chưa có thực đơn, hệ thống hiển thị thông báo và nút tạo mới.

### 4.3 Cập nhật thực đơn

**Mục tiêu:** Sửa nội dung thực đơn hiện có.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Thực đơn tồn tại và thuộc người dùng.

**Hậu điều kiện:** Thực đơn được cập nhật.

**CRUD:** Update.

**Luồng chính:**
1. Người dùng mở thực đơn cần chỉnh sửa.
2. Hệ thống hiển thị giao diện chỉnh sửa.
3. Người dùng thực hiện thay đổi.
4. Người dùng lưu thay đổi.
5. Hệ thống cập nhật dữ liệu và hiển thị thông báo.

**Luồng thay thế:**
2.1. Nếu thực đơn không tồn tại, hệ thống hiển thị lỗi.

#### 4.3.1 Thêm món vào thực đơn

**Mục tiêu:** Bổ sung món ăn mới vào thực đơn hiện tại.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Thực đơn đang ở trạng thái chỉnh sửa.

**Hậu điều kiện:** Món mới được thêm vào thực đơn.

**CRUD:** Update.

**Luồng chính:**
1. Người dùng chọn chức năng thêm món.
2. Người dùng tìm kiếm hoặc chọn món.
3. Người dùng chỉ định khẩu phần.
4. Người dùng lưu cập nhật.
5. Hệ thống cập nhật thực đơn.

**Luồng thay thế:**
3.1. Nếu món đã tồn tại, hệ thống đề xuất điều chỉnh khẩu phần thay vì thêm trùng.

#### 4.3.2 Sửa khẩu phần/loại bữa

**Mục tiêu:** Điều chỉnh tỷ lệ khẩu phần hoặc thay đổi loại bữa.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Có thực đơn và món ăn cần sửa.

**Hậu điều kiện:** Khẩu phần hoặc loại bữa được cập nhật.

**CRUD:** Update.

**Luồng chính:**
1. Người dùng chọn món cần điều chỉnh.
2. Người dùng thay đổi khẩu phần hoặc loại bữa.
3. Người dùng lưu thay đổi.
4. Hệ thống cập nhật và thông báo.

**Luồng thay thế:**
2.1. Nếu giá trị khẩu phần không hợp lệ, hệ thống hiển thị lỗi và yêu cầu người dùng sửa lại.

#### 4.3.3 Thay thế món ăn

**Mục tiêu:** Thay một món trong thực đơn bằng món khác.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Thực đơn có món để thay.

**Hậu điều kiện:** Món cũ được thay bằng món mới.

**CRUD:** Update.

**Luồng chính:**
1. Người dùng chọn món cần thay thế.
2. Người dùng chọn món thay thế từ danh sách.
3. Người dùng xác nhận thay thế.
4. Hệ thống cập nhật thực đơn và thông báo.

**Luồng thay thế:**
2.1. Nếu món thay thế không đủ dữ liệu, hệ thống gợi ý người dùng chọn món khác.

### 4.4 Xóa thực đơn / xóa món khỏi thực đơn

**Mục tiêu:** Loại bỏ toàn bộ thực đơn hoặc chỉ một món.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Thực đơn hoặc món thuộc quyền sở hữu của người dùng.

**Hậu điều kiện:** Thực đơn hoặc món bị xóa.

**CRUD:** Delete.

**Luồng chính:**
1. Người dùng chọn xóa thực đơn hoặc món.
2. Hệ thống yêu cầu xác nhận.
3. Người dùng xác nhận.
4. Hệ thống xóa dữ liệu.
5. Hệ thống cập nhật lại danh sách và hiển thị thông báo.

**Luồng thay thế:**
3.1. Nếu người dùng hủy thao tác, hệ thống giữ nguyên dữ liệu.
4.1. Nếu thực đơn hoặc món đã bị xóa trước đó, hệ thống thông báo không tìm thấy.

### 5.1 Gửi tin nhắn chat

**Mục tiêu:** Cho phép người dùng gửi truy vấn chat đến hệ thống AI.

**Tác nhân:** Người dùng đã đăng nhập hoặc guest.

**Tiền điều kiện:** Phiên chat hiện có hoặc được tạo mới.

**Hậu điều kiện:** Tin nhắn được gửi và phản hồi được sinh.

**CRUD:** Create (tin nhắn).

**Luồng chính:**
1. Người dùng nhập nội dung tin nhắn.
2. Người dùng gửi tin nhắn.
3. Hệ thống kiểm tra tin nhắn.
4. Hệ thống ghi nhận tin nhắn và gọi dịch vụ NLU.
5. Hệ thống xác định ý định và truy xuất dữ liệu liên quan.
6. Hệ thống sinh phản hồi.
7. Hệ thống hiển thị phản hồi cho người dùng.

**Luồng thay thế:**
3.1. Nếu tin nhắn trống, hệ thống yêu cầu người dùng nhập nội dung.
4.1. Nếu dịch vụ AI/NLU lỗi, hệ thống hiển thị thông báo và đề xuất gửi lại.

#### 5.1.1 Phân tích ý định từ tin nhắn

**Mục tiêu:** Xác định mục đích và thực thể từ truy vấn chat.

**Tác nhân:** Hệ thống.

**Tiền điều kiện:** Tin nhắn văn bản đã được ghi nhận.

**Hậu điều kiện:** Ý định và tham số được xác định.

**CRUD:** Read.

**Luồng chính:**
1. Hệ thống gửi nội dung tin nhắn tới mô hình NLU hoặc module phân tích.
2. Hệ thống nhận kết quả intent/pattern.
3. Hệ thống sử dụng kết quả để định hướng truy vấn tiếp theo.

**Luồng thay thế:**
2.1. Nếu không xác định rõ intent, hệ thống chọn trả lời chung hoặc yêu cầu người dùng làm rõ.

#### 5.1.2 Truy xuất dữ liệu liên quan

**Mục tiêu:** Lấy dữ liệu phù hợp theo ý định chat.

**Tác nhân:** Hệ thống.

**Tiền điều kiện:** Ý định đã được xác định.

**Hậu điều kiện:** Dữ liệu liên quan sẵn sàng cho bước sinh phản hồi.

**CRUD:** Read.

**Luồng chính:**
1. Hệ thống xác định nguồn dữ liệu cần truy vấn (thực phẩm, nhật ký, hồ sơ, công thức, v.v.).
2. Hệ thống truy vấn và chuẩn hoá dữ liệu trả về.
3. Hệ thống chuyển dữ liệu cho bước sinh phản hồi.

**Luồng thay thế:**
2.1. Nếu không tìm thấy dữ liệu phù hợp, hệ thống sử dụng nội dung mặc định hoặc yêu cầu người dùng cung cấp thêm thông tin.

#### 5.1.3 Sinh phản hồi

**Mục tiêu:** Sinh câu trả lời chat phù hợp và hữu ích.

**Tác nhân:** Hệ thống / Gemini.

**Tiền điều kiện:** Có ý định và/hoặc dữ liệu liên quan.

**Hậu điều kiện:** Phản hồi được tạo và trả về người dùng.

**CRUD:** Create (bản ghi phản hồi chat).

**Luồng chính:**
1. Hệ thống gửi prompt và dữ liệu liên quan đến dịch vụ AI hoặc module sinh phản hồi.
2. Hệ thống nhận phản hồi văn bản.
3. Hệ thống lưu phản hồi vào phiên chat.
4. Hệ thống hiển thị phản hồi cho người dùng.

**Luồng thay thế:**
2.1. Nếu AI không trả về kết quả, hệ thống hiển thị thông báo lỗi và đề xuất thử lại.

### 5.2 Xem lịch sử chat

**Mục tiêu:** Hiển thị lịch sử tin nhắn và phiên chat.

**Tác nhân:** Người dùng đã đăng nhập hoặc guest.

**Tiền điều kiện:** Có phiên chat và tin nhắn tồn tại.

**Hậu điều kiện:** Không thay đổi dữ liệu.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng mở trang lịch sử chat.
2. Hệ thống truy vấn các phiên và tin nhắn phù hợp với người dùng/phiên.
3. Hệ thống hiển thị danh sách phiên và nội dung tin nhắn.

**Luồng thay thế:**
2.1. Nếu không có lịch sử, hệ thống hiển thị trang trống với hướng dẫn bắt đầu chat.

### 5.3 Xóa phiên chat / tin nhắn

**Mục tiêu:** Xoá lịch sử chat riêng lẻ hoặc toàn bộ phiên.

**Tác nhân:** Người dùng đã đăng nhập hoặc guest.

**Tiền điều kiện:** Phiên hoặc tin nhắn tồn tại.

**Hậu điều kiện:** Dữ liệu chat bị xóa.

**CRUD:** Delete.

**Luồng chính:**
1. Người dùng chọn xóa phiên hoặc tin nhắn.
2. Hệ thống yêu cầu xác nhận.
3. Người dùng xác nhận xóa.
4. Hệ thống xóa phiên/tin nhắn.
5. Hệ thống cập nhật giao diện.

**Luồng thay thế:**
2.1. Nếu người dùng hủy, hệ thống giữ nguyên dữ liệu.
4.1. Nếu dữ liệu đã bị xóa trước đó, hệ thống thông báo không tìm thấy.

### 5.4 Phân tích hành vi sức khỏe

**Mục tiêu:** Cung cấp phân tích sức khỏe dựa trên hành vi ăn uống và chat.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Có dữ liệu nhật ký dinh dưỡng hoặc tương tác chat.

**Hậu điều kiện:** Phân tích và gợi ý được hiển thị.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng yêu cầu phân tích sức khỏe.
2. Hệ thống tổng hợp dữ liệu từ hồ sơ, nhật ký và chat.
3. Hệ thống tính toán chỉ số và gợi ý.
4. Hệ thống hiển thị báo cáo/gợi ý cho người dùng.

**Luồng thay thế:**
2.1. Nếu dữ liệu không đủ, hệ thống yêu cầu người dùng bổ sung hồ sơ hoặc nhật ký.

### 6.1 Xem hồ sơ

**Mục tiêu:** Cho phép người dùng xem thông tin cá nhân và mục tiêu sức khỏe.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Hồ sơ người dùng tồn tại.

**Hậu điều kiện:** Thông tin hồ sơ được hiển thị.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng mở trang hồ sơ.
2. Hệ thống đọc hồ sơ từ DB.
3. Hệ thống hiển thị thông tin cơ thể, mục tiêu và chế độ ăn.
4. Người dùng xem thông tin.

**Luồng thay thế:**
2.1. Nếu hồ sơ chưa có, hệ thống hướng dẫn người dùng tạo hồ sơ mới.

### 6.2 Cập nhật hồ sơ

**Mục tiêu:** Cho phép người dùng cập nhật thông tin hồ sơ.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Hồ sơ tồn tại hoặc có thể tạo mới.

**Hậu điều kiện:** Hồ sơ được cập nhật.

**CRUD:** Update.

**Luồng chính:**
1. Người dùng mở trang chỉnh sửa hồ sơ.
2. Người dùng chỉnh sửa trường thông tin.
3. Người dùng gửi thay đổi.
4. Hệ thống kiểm tra và lưu hồ sơ.
5. Hệ thống hiển thị thông báo thành công.

**Luồng thay thế:**
3.1. Nếu dữ liệu không hợp lệ, hệ thống hiển thị lỗi và yêu cầu sửa.

#### 6.2.1 Cập nhật chỉ số cơ thể

**Mục tiêu:** Sửa cân nặng, chiều cao, tuổi hoặc chỉ số BMI.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Hồ sơ tồn tại.

**Hậu điều kiện:** Chỉ số cơ thể được cập nhật.

**CRUD:** Update.

**Luồng chính:**
1. Người dùng sửa chỉ số cơ thể.
2. Người dùng lưu thay đổi.
3. Hệ thống xác thực và cập nhật thông tin.

**Luồng thay thế:**
2.1. Nếu giá trị không hợp lệ, hệ thống báo lỗi và yêu cầu nhập lại.

#### 6.2.2 Cập nhật mục tiêu sức khỏe

**Mục tiêu:** Thay đổi mục tiêu calo, macro hoặc cân nặng.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Hồ sơ tồn tại.

**Hậu điều kiện:** Mục tiêu mới được lưu.

**CRUD:** Update.

**Luồng chính:**
1. Người dùng chọn mục tiêu mới.
2. Người dùng lưu thay đổi.
3. Hệ thống xác thực và cập nhật.

**Luồng thay thế:**
2.1. Nếu mục tiêu không rõ ràng, hệ thống yêu cầu bổ sung chi tiết.

#### 6.2.3 Cập nhật chế độ ăn

**Mục tiêu:** Cập nhật sở thích hoặc chế độ ăn đặc thù.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Hồ sơ tồn tại.

**Hậu điều kiện:** Chế độ ăn được lưu.

**CRUD:** Update.

**Luồng chính:**
1. Người dùng chọn chế độ ăn (ví dụ: ăn kiêng, ăn chay).
2. Người dùng lưu thay đổi.
3. Hệ thống cập nhật hồ sơ.

**Luồng thay thế:**
2.1. Nếu chế độ ăn không hợp lệ, hệ thống yêu cầu chọn lại.

### 6.3 Tính mục tiêu dinh dưỡng

**Mục tiêu:** Tính toán mục tiêu dinh dưỡng dựa trên hồ sơ cá nhân.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Hồ sơ cá nhân có chỉ số cơ thể và mục tiêu rõ ràng.

**Hậu điều kiện:** Mục tiêu calo/macro được thiết lập.

**CRUD:** Read.

**Luồng chính:**
1. Người dùng yêu cầu tính mục tiêu.
2. Hệ thống sử dụng hàm tính để xác định mục tiêu.
3. Hệ thống hiển thị mục tiêu.
4. Nếu người dùng xác nhận, hệ thống lưu cấu hình.

**Luồng thay thế:**
2.1. Nếu thiếu dữ liệu cơ thể, hệ thống yêu cầu bổ sung.

### 6.4 Xóa tài khoản/dữ liệu hồ sơ

**Mục tiêu:** Xóa tài khoản người dùng và dữ liệu liên quan.

**Tác nhân:** Người dùng đã đăng nhập.

**Tiền điều kiện:** Người dùng xác thực và yêu cầu xóa.

**Hậu điều kiện:** Tài khoản và dữ liệu liên quan bị xóa.

**CRUD:** Delete.

**Luồng chính:**
1. Người dùng mở chức năng xóa tài khoản.
2. Người dùng xác nhận và nhập mật khẩu nếu cần.
3. Hệ thống xóa dữ liệu con trước, rồi xóa tài khoản.
4. Hệ thống đăng xuất người dùng.
5. Hệ thống hiển thị thông báo hoàn tất.

**Luồng thay thế:**
2.1. Nếu người dùng hủy xác nhận, hệ thống không thực hiện xóa.
2.2. Nếu mật khẩu sai, hệ thống từ chối và thông báo lỗi.

### 7.1 Đăng nhập trang quản trị

**Mục tiêu:** Cho phép quản trị viên truy cập giao diện quản trị.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Tài khoản admin hợp lệ.

**Hậu điều kiện:** Admin vào được dashboard quản trị.

**CRUD:** Read.

**Luồng chính:**
1. Admin mở trang login quản trị.
2. Admin nhập thông tin đăng nhập.
3. Hệ thống xác minh quyền quản trị.
4. Hệ thống chuyển đến trang quản trị.

**Luồng thay thế:**
3.1. Nếu không phải admin, hệ thống từ chối quyền truy cập.
3.2. Nếu sai thông tin, hệ thống báo lỗi.

### 7.2 Nhập dữ liệu

**Mục tiêu:** Cập nhật dữ liệu nền bằng cách nhập file hoặc gọi API.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Admin đăng nhập quản trị.

**Hậu điều kiện:** Dữ liệu mới được nhập.

**CRUD:** Create / Update.

**Luồng chính:**
1. Admin chọn chức năng nhập dữ liệu.
2. Admin chọn file hoặc nguồn dữ liệu.
3. Hệ thống xử lý dữ liệu và lưu các bản ghi.
4. Hệ thống hiển thị kết quả.

**Luồng thay thế:**
3.1. Nếu file sai định dạng, hệ thống thông báo lỗi.
3.2. Nếu dữ liệu trùng lặp, hệ thống xử lý theo chính sách duplicate.

### 7.3 Quản lý thực phẩm (CRUD)

**Mục tiêu:** Quản lý danh sách thực phẩm và thông tin dinh dưỡng phục vụ cho nhật ký ăn uống, thực đơn và các gợi ý sức khỏe.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Admin đã đăng nhập và có quyền quản trị dữ liệu.

**Hậu điều kiện:** Dữ liệu thực phẩm được lưu trữ nhất quán, đầy đủ và sẵn sàng sử dụng cho các chức năng chính của hệ thống.

**CRUD:** Create, Read, Update, Delete.

**Dữ liệu chính cần quản lý:**
- Tên thực phẩm
- Danh mục/nhóm thực phẩm
- Đơn vị đo (g, ml, lát, cốc, ...)
- Giá trị dinh dưỡng cơ bản: calo, protein, carbohydrate, chất béo, đường, chất xơ
- Thông tin bổ sung: ảnh, mô tả, nguồn dữ liệu, trạng thái hiển thị

**Luồng chính:**
1. Admin vào trang quản lý thực phẩm.
2. Hệ thống hiển thị danh sách thực phẩm theo phân trang, có bộ lọc theo nhóm, từ khóa và trạng thái.
3. Admin chọn một trong các thao tác: thêm mới, xem chi tiết, sửa, hoặc xóa.
4. Hệ thống thực hiện thao tác tương ứng và cập nhật dữ liệu.
5. Hệ thống thông báo kết quả và cập nhật lại danh sách.

**Luồng thay thế:**
2.1. Nếu không có dữ liệu thực phẩm, hệ thống hiển thị trạng thái trống và hướng dẫn thêm mới.
3.1. Nếu thực phẩm không tồn tại, hệ thống báo lỗi và không cho phép sửa/xóa.
3.2. Nếu thông tin nhập không hợp lệ, hệ thống chặn thao tác và yêu cầu người dùng nhập lại.
4.1. Nếu bản ghi đang được sử dụng bởi nhật ký ăn uống, thực đơn hoặc các báo cáo, hệ thống cảnh báo admin về tác động trước khi xóa.

#### 7.3.1 Thêm thực phẩm

**Mục tiêu:** Tạo bản ghi thực phẩm mới và đưa vào kho dữ liệu hệ thống.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Admin đã đăng nhập và có quyền quản trị thực phẩm.

**Hậu điều kiện:** Thực phẩm mới được lưu trong hệ thống và có thể được sử dụng trong nhật ký ăn uống và thực đơn.

**CRUD:** Create.

**Dữ liệu đầu vào bắt buộc:**
- Tên thực phẩm
- Nhóm thực phẩm
- Đơn vị đo
- Giá trị dinh dưỡng tối thiểu: calo

**Dữ liệu đầu vào tùy chọn:**
- Protein, carbohydrate, chất béo, đường, chất xơ
- Mô tả
- Nguồn dữ liệu
- URL ảnh

**Luồng chính:**
1. Admin chọn chức năng "Thêm thực phẩm".
2. Hệ thống hiển thị form nhập liệu với các trường bắt buộc và tùy chọn.
3. Admin nhập thông tin thực phẩm.
4. Hệ thống kiểm tra dữ liệu theo quy tắc:
   - Tên không được rỗng
   - Giá trị dinh dưỡng phải là số >= 0
   - Đơn vị đo phải thuộc danh sách hỗ trợ
5. Hệ thống kiểm tra trùng lặp tên + đơn vị + nhóm thực phẩm.
6. Hệ thống lưu bản ghi.
7. Hệ thống hiển thị thông báo thành công và chuyển về danh sách thực phẩm.

**Luồng thay thế:**
3.1. Nếu thiếu dữ liệu bắt buộc, hệ thống báo lỗi và giữ lại form.
4.1. Nếu giá trị dinh dưỡng nhập sai định dạng, hệ thống yêu cầu nhập lại.
5.1. Nếu thực phẩm đã tồn tại, hệ thống báo trùng lặp và yêu cầu admin xác nhận cập nhật hoặc chọn tên khác.
6.1. Nếu lưu thất bại do lỗi hệ thống, hệ thống thông báo lỗi và ghi log.

#### 7.3.2 Xem danh sách/chi tiết thực phẩm

**Mục tiêu:** Quan sát danh sách thực phẩm và xem chi tiết dữ liệu dinh dưỡng của từng thực phẩm.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Admin đã đăng nhập.

**Hậu điều kiện:** Thông tin thực phẩm được hiển thị đầy đủ cho mục đích tra cứu hoặc chỉnh sửa.

**CRUD:** Read.

**Luồng chính:**
1. Admin mở trang quản lý thực phẩm.
2. Hệ thống truy vấn danh sách thực phẩm với lọc theo từ khóa, nhóm và trạng thái.
3. Hệ thống hiển thị danh sách kết quả.
4. Admin chọn một thực phẩm để xem chi tiết.
5. Hệ thống hiển thị thông tin đầy đủ, bao gồm dữ liệu dinh dưỡng, mô tả, nguồn và trạng thái.

**Luồng thay thế:**
2.1. Nếu không có kết quả, hệ thống hiển thị trạng thái trống.
4.1. Nếu thực phẩm đã bị xóa hoặc không tồn tại, hệ thống thông báo không tìm thấy.

#### 7.3.3 Sửa thông tin thực phẩm

**Mục tiêu:** Cập nhật thông tin của một thực phẩm đã tồn tại.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Bản ghi thực phẩm tồn tại và admin có quyền chỉnh sửa.

**Hậu điều kiện:** Thông tin thực phẩm được cập nhật và phản ánh đúng trên hệ thống.

**CRUD:** Update.

**Các trường có thể cập nhật:**
- Tên thực phẩm
- Nhóm thực phẩm
- Đơn vị đo
- Mô tả
- Thông tin dinh dưỡng
- Ảnh
- Trạng thái hiển thị

**Luồng chính:**
1. Admin tìm thực phẩm cần sửa.
2. Hệ thống hiển thị màn hình chỉnh sửa với dữ liệu hiện tại.
3. Admin thay đổi trường cần thiết.
4. Hệ thống kiểm tra tính hợp lệ và trùng lặp.
5. Hệ thống cập nhật bản ghi.
6. Hệ thống hiển thị thông báo cập nhật thành công.

**Luồng thay thế:**
3.1. Nếu admin xóa bỏ toàn bộ dữ liệu bắt buộc, hệ thống báo lỗi và chặn lưu.
4.1. Nếu giá trị dinh dưỡng không hợp lệ, hệ thống yêu cầu chỉnh sửa.
5.1. Nếu xảy ra lỗi cập nhật, hệ thống thông báo thất bại và giữ nguyên dữ liệu cũ.

#### 7.3.4 Xóa thực phẩm

**Mục tiêu:** Loại bỏ một thực phẩm khỏi hệ thống khi không còn cần sử dụng.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Bản ghi thực phẩm tồn tại và admin đủ quyền.

**Hậu điều kiện:** Thực phẩm bị xóa hoặc chuyển sang trạng thái vô hiệu nếu hệ thống yêu cầu mềm-delete.

**CRUD:** Delete.

**Luồng chính:**
1. Admin chọn thực phẩm cần xóa.
2. Hệ thống hiển thị hộp thoại xác nhận kèm cảnh báo về ảnh hưởng dữ liệu.
3. Admin xác nhận xóa.
4. Hệ thống kiểm tra các ràng buộc:
   - Thực phẩm có đang được sử dụng trong nhật ký ăn uống, thực đơn, hoặc bản ghi lịch sử?
   - Có tồn tại dữ liệu liên quan không thể xóa trực tiếp?
5. Hệ thống thực hiện thao tác xóa hoặc chuyển trạng thái vô hiệu.
6. Hệ thống cập nhật danh sách và thông báo kết quả.

**Luồng thay thế:**
2.1. Nếu admin hủy thao tác, hệ thống không thay đổi dữ liệu.
4.1. Nếu bản ghi đang được dùng và xóa gây mất dữ liệu lịch sử, hệ thống yêu cầu xác nhận bổ sung hoặc từ chối thao tác.
5.1. Nếu xóa thất bại, hệ thống thông báo lỗi và không thay đổi dữ liệu.

### 7.4 Quản lý ý định chat (CRUD)

**Mục tiêu:** Quản lý intent và pattern phục vụ chat AI.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Admin đăng nhập.

**Hậu điều kiện:** Intent/pattern được duy trì.

**CRUD:** Create, Read, Update, Delete.

#### 7.4.1 Thêm intent/pattern

**Mục tiêu:** Tạo intent hoặc mẫu pattern mới.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Đã đăng nhập.

**Hậu điều kiện:** Intent/pattern mới tồn tại.

**CRUD:** Create.

**Luồng chính:**
1. Admin chọn chức năng thêm.
2. Admin nhập tên, mẫu và phản hồi.
3. Admin lưu.

**Luồng thay thế:**
2.1. Nếu tên hoặc mẫu trùng, hệ thống cảnh báo.

#### 7.4.2 Xem danh sách/chi tiết intent

**Mục tiêu:** Tra cứu intent và pattern hiện có.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Đã đăng nhập.

**Hậu điều kiện:** Hiển thị chi tiết intent.

**CRUD:** Read.

**Luồng chính:**
1. Admin mở danh sách intent.
2. Admin chọn intent để xem chi tiết.

**Luồng thay thế:**
2.1. Nếu không có intent, hệ thống hiển thị trạng thái trống.

#### 7.4.3 Sửa intent/pattern

**Mục tiêu:** Cập nhật nội dung intent hoặc pattern.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Intent tồn tại.

**Hậu điều kiện:** Intent được cập nhật.

**CRUD:** Update.

**Luồng chính:**
1. Admin chọn intent.
2. Admin sửa nội dung.
3. Admin lưu.

**Luồng thay thế:**
2.1. Nếu mẫu không hợp lệ, hệ thống yêu cầu sửa lại.

#### 7.4.4 Xóa intent/pattern

**Mục tiêu:** Xoá intent/pattern không sử dụng.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Intent tồn tại.

**Hậu điều kiện:** Intent bị xóa.

**CRUD:** Delete.

**Luồng chính:**
1. Admin chọn xóa.
2. Hệ thống yêu cầu xác nhận.
3. Admin xác nhận.
4. Hệ thống xóa intent.

**Luồng thay thế:**
3.1. Nếu intent đang được sử dụng, hệ thống cảnh báo hoặc từ chối.

### 7.5 Quản lý người dùng (CRUD)

**Mục tiêu:** Quản lý tài khoản người dùng, quyền truy cập và trạng thái hoạt động của người dùng trong hệ thống.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Admin đã đăng nhập và có quyền quản trị người dùng.

**Hậu điều kiện:** Hồ sơ người dùng được duy trì đầy đủ, quyền truy cập được kiểm soát và trạng thái tài khoản phản ánh đúng thực tế.

**CRUD:** Create, Read, Update, Delete.

**Dữ liệu chính cần quản lý:**
- Tên đăng nhập / email
- Vai trò người dùng (user, admin, hoặc vai trò mở rộng)
- Trạng thái tài khoản (hoạt động, tạm khóa, vô hiệu hóa)
- Thông tin hồ sơ liên kết
- Ngày tạo, ngày cập nhật, lần đăng nhập gần nhất

**Luồng chính:**
1. Admin mở trang quản lý người dùng.
2. Hệ thống hiển thị danh sách người dùng với bộ lọc theo vai trò, trạng thái và từ khóa.
3. Admin chọn thao tác: thêm người dùng, xem chi tiết, cập nhật vai trò/trạng thái, hoặc xóa/vô hiệu hóa.
4. Hệ thống thực hiện thao tác và cập nhật danh sách.
5. Hệ thống thông báo kết quả.

**Luồng thay thế:**
2.1. Nếu không có người dùng, hệ thống hiển thị trạng thái trống.
3.1. Nếu tài khoản không tồn tại, hệ thống báo lỗi và yêu cầu chọn lại.
3.2. Nếu dữ liệu đầu vào không hợp lệ, hệ thống chặn thao tác và hiển thị lỗi.
4.1. Nếu thao tác thay đổi quyền hoặc trạng thái ảnh hưởng đến quản trị hệ thống, hệ thống cảnh báo trước khi lưu.

#### 7.5.1 Thêm/mời người dùng

**Mục tiêu:** Tạo tài khoản mới hoặc gửi lời mời tham gia hệ thống.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Admin đã đăng nhập và quyền quản trị người dùng hợp lệ.

**Hậu điều kiện:** Tài khoản mới được tạo hoặc lời mời được gửi thành công.

**CRUD:** Create.

**Dữ liệu đầu vào bắt buộc:**
- Email
- Vai trò người dùng

**Dữ liệu đầu vào tùy chọn:**
- Tên hiển thị
- Mật khẩu tạm thời (nếu tạo trực tiếp)
- Ghi chú

**Luồng chính:**
1. Admin mở form thêm/mời người dùng.
2. Hệ thống hiển thị các trường cần thiết và tùy chọn gửi lời mời hoặc tạo tài khoản ngay.
3. Admin nhập email, vai trò và các thông tin bổ sung nếu cần.
4. Hệ thống kiểm tra:
   - Email đúng định dạng
   - Email chưa tồn tại trong hệ thống
   - Vai trò hợp lệ
5. Hệ thống tạo tài khoản hoặc gửi lời mời.
6. Hệ thống thông báo thành công và cập nhật danh sách.

**Luồng thay thế:**
3.1. Nếu email đã tồn tại, hệ thống báo lỗi và yêu cầu dùng email khác.
4.1. Nếu mật khẩu không đạt quy tắc bảo mật, hệ thống yêu cầu nhập lại.
5.1. Nếu gửi email lời mời thất bại, hệ thống báo lỗi và cho phép admin thử lại hoặc tạo tài khoản trực tiếp.

#### 7.5.2 Xem danh sách/chi tiết người dùng

**Mục tiêu:** Theo dõi người dùng trong hệ thống và kiểm tra thông tin chi tiết của từng tài khoản.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Admin đã đăng nhập.

**Hậu điều kiện:** Danh sách người dùng và chi tiết từng tài khoản được hiển thị đầy đủ.

**CRUD:** Read.

**Luồng chính:**
1. Admin mở trang quản lý người dùng.
2. Hệ thống truy vấn danh sách người dùng theo bộ lọc.
3. Hệ thống hiển thị thông tin tổng quan: email, vai trò, trạng thái, ngày tạo, lần đăng nhập gần nhất.
4. Admin chọn một tài khoản để xem chi tiết.
5. Hệ thống hiển thị thông tin hồ sơ liên kết, quyền, lịch sử đăng nhập và trạng thái tài khoản.

**Luồng thay thế:**
2.1. Nếu không có tài khoản phù hợp, hệ thống hiển thị trạng thái trống.
4.1. Nếu tài khoản không tồn tại, hệ thống báo lỗi và quay về danh sách.

#### 7.5.3 Cập nhật vai trò/trạng thái

**Mục tiêu:** Điều chỉnh quyền truy cập hoặc trạng thái hoạt động của người dùng.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Tài khoản người dùng tồn tại và admin có quyền thay đổi.

**Hậu điều kiện:** Vai trò và/hoặc trạng thái người dùng được cập nhật.

**CRUD:** Update.

**Các thao tác có thể thực hiện:**
- Thay đổi vai trò (user → admin hoặc ngược lại)
- Khóa/mở khóa tài khoản
- Vô hiệu hóa/tái kích hoạt tài khoản

**Luồng chính:**
1. Admin chọn tài khoản cần chỉnh sửa.
2. Hệ thống hiển thị form cập nhật vai trò và trạng thái.
3. Admin thay đổi quyền hoặc trạng thái.
4. Hệ thống kiểm tra ràng buộc:
   - Không được hủy quyền admin của toàn bộ admin đang hoạt động
   - Trạng thái phải thuộc tập hợp hợp lệ
5. Hệ thống lưu thay đổi.
6. Hệ thống thông báo cập nhật thành công.

**Luồng thay thế:**
3.1. Nếu admin cố gắng xóa quyền cuối cùng của admin đang hoạt động, hệ thống cảnh báo và yêu cầu chọn admin khác.
4.1. Nếu thay đổi trạng thái gây mất quyền truy cập tạm thời, hệ thống yêu cầu xác nhận.
5.1. Nếu cập nhật thất bại, hệ thống báo lỗi và không thay đổi dữ liệu.

#### 7.5.4 Xóa/vô hiệu hóa người dùng

**Mục tiêu:** Loại bỏ hoặc vô hiệu hóa tài khoản người dùng không còn phù hợp.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Tài khoản tồn tại và admin có quyền thao tác.

**Hậu điều kiện:** Tài khoản bị xóa khỏi hệ thống hoặc chuyển sang trạng thái vô hiệu hóa.

**CRUD:** Delete / Update.

**Luồng chính:**
1. Admin chọn tài khoản cần xóa hoặc vô hiệu hóa.
2. Hệ thống hiển thị xác nhận với cảnh báo về tác động.
3. Admin xác nhận thao tác.
4. Hệ thống kiểm tra:
   - Có phải tài khoản admin duy nhất?
   - Có dữ liệu liên quan cần xử lý trước khi xóa?
5. Hệ thống thực hiện xóa hoặc vô hiệu hóa.
6. Hệ thống cập nhật danh sách và thông báo kết quả.

**Luồng thay thế:**
2.1. Nếu admin hủy thao tác, hệ thống giữ nguyên dữ liệu.
4.1. Nếu đây là tài khoản admin cuối cùng, hệ thống từ chối và yêu cầu chỉ định admin khác.
5.1. Nếu dữ liệu liên quan không thể xóa trực tiếp, hệ thống chuyển sang cơ chế vô hiệu hóa hoặc yêu cầu xử lý bổ sung.

### 7.6 Dọn dữ liệu trùng/lỗi

**Mục tiêu:** Kiểm tra và làm sạch dữ liệu sai hoặc trùng lặp.

**Tác nhân:** Quản trị viên.

**Tiền điều kiện:** Quản trị viên có quyền quản lý dữ liệu.

**Hậu điều kiện:** Dữ liệu được làm sạch hoặc gắn cờ sai lệch.

**CRUD:** Update / Delete.

**Luồng chính:**
1. Admin mở chức năng dọn dữ liệu.
2. Hệ thống phân tích dữ liệu và tìm bản ghi trùng/lỗi.
3. Hệ thống hiển thị báo cáo.
4. Admin chọn xóa hoặc sửa các bản ghi.

**Luồng thay thế:**
2.1. Nếu không tìm thấy trùng/lỗi, hệ thống hiển thị trạng thái sạch.
4.1. Nếu thao tác xóa gây ảnh hưởng dữ liệu liên quan, hệ thống cảnh báo trước.

---

## 4. Ghi chú

- Tất cả use case có thể mở rộng thêm luồng phụ để xử lý lỗi dịch vụ bên ngoài, lỗi mạng hoặc lỗi xác thực.
- Các use case thuộc menu quản trị cần kiểm tra quyền trước khi thực hiện CRUD.
- Các luồng AI chat có thể tái sử dụng thông tin intent/pattern để tối ưu phản hồi.
