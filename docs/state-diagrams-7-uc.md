# Sơ đồ trạng thái cho 7 use case lớn

Tài liệu này chuyển 7 use case lớn sang sơ đồ trạng thái theo quy ước đã nêu: một trạng thái khởi đầu, các trạng thái chính, nhánh lựa chọn và các chuyển tiếp có trigger/guard/behavior.

## 1. Xác thực & phân quyền

```mermaid
stateDiagram-v2
    [*] --> Guest
    Guest --> RegisterForm: mở_đăng_ký
    Guest --> LoginForm: mở_đăng_nhập
    Guest --> AdminLoginForm: mở_đăng_nhập_quản_trị

    RegisterForm --> ValidateRegister: submit_register
    ValidateRegister --> RegisterError: [form_invalid || email_exists || username_exists] / hiển_thị_lỗi
    ValidateRegister --> AccountCreated: [valid && unique] / tạo_tài_khoản
    RegisterError --> RegisterForm: sửa_lại_thông_tin

    AccountCreated --> LoginForm: chuyển_đến_đăng_nhập

    LoginForm --> ValidateLogin: submit_login
    ValidateLogin --> Authenticated: [credentials_valid && !locked] / tạo_session
    ValidateLogin --> LoginError: [credentials_invalid || account_missing] / hiển_thị_lỗi
    ValidateLogin --> LockedNotice: [account_locked] / thông_báo_khóa
    LoginError --> LoginForm: nhập_lại
    LockedNotice --> [*]

    Authenticated --> Logout: logout
    Logout --> Guest: huỷ_session

    AdminLoginForm --> ValidateAdminLogin: submit_admin_login
    ValidateAdminLogin --> AdminAuthenticated: [admin_valid] / tạo_session_admin
    ValidateAdminLogin --> AdminDenied: [!admin_valid] / từ_chối_truy_cập
    AdminDenied --> AdminLoginForm: thử_lại
    AdminAuthenticated --> Logout: logout
```

## 2. Theo dõi dinh dưỡng

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated
    Unauthenticated --> Authenticated: login_success

    Authenticated --> NutritionLogEntry: mở_thêm_nhật_ký
    NutritionLogEntry --> SearchFood: tìm_kiếm_thực_phẩm
    SearchFood --> NoResult: [result_empty] / hiển_thị_gợi_ý
    NoResult --> SearchFood: điều_chỉnh_từ_khoá
    SearchFood --> FoodDetail: chọn_thực_phẩm
    FoodDetail --> CalculateIntake: nhập_khẩu_phần
    CalculateIntake --> IntakeError: [portion_invalid] / thông_báo_lỗi
    IntakeError --> CalculateIntake: sửa_khẩu_phần
    CalculateIntake --> NutritionLogEntry: cập_nhật_tổng_dinh_dưỡng
    NutritionLogEntry --> SaveLog: xác_nhận_lưu
    SaveLog --> NutritionSaved: [account_exists] / lưu_bản_ghi
    SaveLog --> AuthError: [!account_exists] / yêu_cầu_đăng_nhập
    NutritionSaved --> ViewLogs: xem_nhật_ký

    ViewLogs --> UpdateLog: chọn_sửa
    UpdateLog --> ValidateUpdate: lưu_thay_đổi
    ValidateUpdate --> UpdateError: [invalid_input] / hiển_thị_cảnh_báo
    UpdateError --> UpdateLog: sửa_lại
    ValidateUpdate --> NutritionUpdated: [valid_input] / cập_nhật_bản_ghi

    ViewLogs --> DeleteLog: chọn_xóa
    DeleteLog --> DeletedLog: xác_nhận_xóa
    DeletedLog --> ViewLogs: quay_lại

    ViewLogs --> EmptyState: [no_logs] / hiển_thị_trống
    EmptyState --> NutritionLogEntry: tạo_bản_ghi_mới

    Authenticated --> [*]
```

## 3. Bảng điều khiển & phân tích

```mermaid
stateDiagram-v2
    [*] --> Authenticated
    Authenticated --> DashboardLoading: mở_bảng_điều_khiển
    DashboardLoading --> DailyDashboard: [metrics_ready] / tải_thống_kê_ngày
    DashboardLoading --> DataMissing: [metrics_missing] / hiển_thị_bổ_sung
    DataMissing --> NutritionLogEntry: thêm_bản_ghi
    DailyDashboard --> CompareNutrition: so_sánh_dinh_dưỡng
    DailyDashboard --> SuggestNutrition: nhận_gợi_ý
    CompareNutrition --> DailyDashboard: quay_lại
    SuggestNutrition --> DailyDashboard: quay_lại
    DailyDashboard --> [*]
```

## 4. Lập thực đơn

```mermaid
stateDiagram-v2
    [*] --> Authenticated
    Authenticated --> MealPlanEntry: mở_lập_thực_đơn
    MealPlanEntry --> ChooseSource: chọn_cách_tạo

    ChooseSource --> ManualPlan: [source == manual] / nhập_thủ_công
    ChooseSource --> AIGeneratedPlan: [source == ai] / tạo_tự_động

    ManualPlan --> PlanForm: nhập_món_ăn
    PlanForm --> PlanValidation: lưu_thực_đơn
    PlanValidation --> PlanSaved: [valid_input && account_exists] / lưu_thực_đơn
    PlanValidation --> PlanError: [invalid_input || !account_exists] / hiển_thị_lỗi
    PlanError --> PlanForm: sửa_lại

    AIGeneratedPlan --> GeneratedPlan: nhận_kết_quả_AI
    GeneratedPlan --> PlanSaved: xác_nhận_lưu

    PlanSaved --> ViewMealPlan: xem_thực_đơn
    ViewMealPlan --> UpdateMealPlan: chỉnh_sửa
    UpdateMealPlan --> AddMeal: thêm_món
    UpdateMealPlan --> EditServing: sửa_khẩu_phần
    UpdateMealPlan --> ReplaceMeal: thay_thế_món
    UpdateMealPlan --> DeletePlan: xóa_thực_đơn

    AddMeal --> UpdateMealPlan: hoàn_tất
    EditServing --> UpdateMealPlan: hoàn_tất
    ReplaceMeal --> UpdateMealPlan: hoàn_tất
    DeletePlan --> MealPlanEntry: xác_nhận_xóa

    ViewMealPlan --> [*]
```

## 5. Tư vấn chat AI

```mermaid
stateDiagram-v2
    [*] --> Authenticated
    Authenticated --> ChatReady: mở_chat
    ChatReady --> ComposeMessage: nhập_tin_nhắn
    ComposeMessage --> IntentAnalysis: gửi_tin_nhắn

    IntentAnalysis --> RetrieveData: [intent_needs_context] / truy_vấn_dữ_liệu
    IntentAnalysis --> AIResponse: [intent_simple] / sinh_phản_hồi
    RetrieveData --> AIResponse: nhận_dữ_liệu_liên_quan

    AIResponse --> ChatReady: hiển_thị_phản_hồi
    ChatReady --> ViewHistory: xem_lịch_sử
    ViewHistory --> ChatReady: quay_lại

    ChatReady --> DeleteConversation: xóa_phiên
    DeleteConversation --> ChatReady: xác_nhận_xóa

    ChatReady --> HealthBehaviorAnalysis: phân_tích_hành_vi_sức_khỏe
    HealthBehaviorAnalysis --> ChatReady: hoàn_tất
```

## 6. Hồ sơ người dùng

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated
    Unauthenticated --> Authenticated: login_success

    Authenticated --> ProfileView: mở_hồ_sơ
    ProfileView --> EditProfile: chỉnh_sửa_hồ_sơ
    EditProfile --> UpdateBodyMetrics: cập_nhật_chỉ_số_cơ_thể
    EditProfile --> UpdateGoals: cập_nhật_mục_tiêu_sức_khỏe
    EditProfile --> UpdateDiet: cập_nhật_chế_độ_ăn
    UpdateBodyMetrics --> CalculateTargets: lưu
    UpdateGoals --> CalculateTargets: lưu
    UpdateDiet --> CalculateTargets: lưu

    CalculateTargets --> SaveProfile: tính_mục_tiêu_dinh_dưỡng
    SaveProfile --> ProfileSaved: [account_exists] / lưu_hồ_sơ
    SaveProfile --> ProfileError: [!account_exists] / yêu_cầu_đăng_nhập
    ProfileError --> EditProfile: sửa_lại

    ProfileView --> DeleteAccount: xóa_tài_khoản
    DeleteAccount --> Guest: xác_nhận_xóa

    ProfileSaved --> ProfileView: quay_lại
    ProfileView --> [*]
```

## 7. Quản trị dữ liệu

```mermaid
stateDiagram-v2
    [*] --> AdminLoginForm
    AdminLoginForm --> ValidateAdminLogin: submit_admin_login
    ValidateAdminLogin --> AdminAuthenticated: [admin_valid] / tạo_session_admin
    ValidateAdminLogin --> AdminDenied: [!admin_valid] / thông_báo_từ_chối
    AdminDenied --> AdminLoginForm: thử_lại

    AdminAuthenticated --> AdminDashboard: mở_trang_quản_trị
    AdminDashboard --> ManageFoods: quản_lý_thực_phẩm
    AdminDashboard --> ManageIntents: quản_lý_ý_định_chat
    AdminDashboard --> ManageUsers: quản_lý_người_dùng
    AdminDashboard --> CleanupData: dọn_dữ_liệu_trùng_lỗi

    ManageFoods --> FoodCreate: thêm_thực_phẩm
    FoodCreate --> FoodRead: xem_danh_sách
    FoodRead --> FoodUpdate: sửa_thông_tin
    FoodUpdate --> FoodDelete: xóa_thực_phẩm
    FoodDelete --> ManageFoods: hoàn_tất

    ManageIntents --> IntentCreate: thêm_intent
    IntentCreate --> IntentRead: xem_chi_tiết
    IntentRead --> IntentUpdate: sửa_intent
    IntentUpdate --> IntentDelete: xóa_intent
    IntentDelete --> ManageIntents: hoàn_tất

    ManageUsers --> UserCreate: thêm_người_dùng
    UserCreate --> UserRead: xem_danh_sách
    UserRead --> UserUpdate: cập_nhật_vai_trò_trạng_thái
    UserUpdate --> UserDelete: vô_hiệu_hóa_xóa
    UserDelete --> ManageUsers: hoàn_tất

    CleanupData --> AdminDashboard: hoàn_tất
    AdminDashboard --> Logout: logout
    Logout --> [*]
```

## Ghi chú triển khai

- Các trạng thái `Authenticated` / `AdminAuthenticated` là các trạng thái nền tảng cần được bảo vệ bằng session và quyền truy cập.
- Các nhánh `[...]` thể hiện `Guard` theo quy ước yêu cầu.
- Các hành vi `/ ...` thể hiện `Behavior` khi chuyển trạng thái.
- Nếu muốn, tôi có thể tiếp tục chuyển từng sơ đồ này thành bảng trạng thái chi tiết theo từng màn hình UI hoặc thành file ảnh/PlantUML.
