# THIẾT KẾ KIẾN TRÚC TỔNG THỂ HỆ THỐNG (SYSTEM ARCHITECTURE)
## ĐỀ TÀI: NGHIÊN CỨU VÀ PHÁT TRIỂN ỨNG DỤNG WEB TRỢ LÝ NỘI TRỢ THÔNG MINH DỰA TRÊN PHÂN TÍCH DỮ LIỆU VÀ CÁ NHÂN HÓA THỰC ĐƠN SỬ DỤNG DJANGO VÀ POSTGRESQL

Để đồ án tốt nghiệp của bạn đạt tiêu chuẩn kỹ thuật cao, phần kiến trúc hệ thống nên được mô tả bằng **Mô hình C4 (C4 Model)** - tiêu chuẩn công nghiệp hiện đại dùng để trực quan hóa kiến trúc phần mềm theo các mức độ chi tiết khác nhau.

Dưới đây là thiết kế kiến trúc chi tiết từ mức ngữ cảnh (Context), phân rã ứng dụng (Container), chi tiết thành phần bên trong (Component) cho đến sơ đồ quan hệ cơ sở dữ liệu (ERD).

---

## 1. C4 - LEVEL 1: SƠ ĐỒ NGỮ CẢNH HỆ THỐNG (SYSTEM CONTEXT DIAGRAM)

Sơ đồ này mô tả ranh giới của hệ thống **Smart Home Chef**, các tác nhân (User, Admin) tương tác với hệ thống và các dịch vụ bên ngoài (Gemini API, Spoonacular API, Siêu thị WinMart/BHX).

```mermaid
graph TB
    %% Actors
    U["Người Dùng Cuối (User)<br>[Tìm món ăn, nhận thực đơn cá nhân hóa, chat dinh dưỡng]"]
    A["Quản Trị Viên (Admin/Data Steward)<br>[Duyệt thực phẩm thô, quản lý cấu hình mô hình]"]

    %% System
    S["Hệ Thống Smart Home Chef<br>[Ứng dụng Web Django & PostgreSQL]"]

    %% External Systems
    G["Google Gemini API<br>[LLM Service - Hỗ trợ NLU & Fallback Generation]"]
    SP["Spoonacular API<br>[Dịch vụ dinh dưỡng vi lượng ngoại vi]"]
    W["Website Thương Mại Điện Tử<br>[WinMart / Bách Hóa Xanh - Nguồn crawl giá]"]

    %% Relationships
    U -->|"Sử dụng trình duyệt, tương tác với"| S
    A -->|"Quản trị dữ liệu, phê duyệt hàng đợi tại"| S
    S -->|"Crawl dữ liệu sản phẩm & giá từ"| W
    S -->|"Gửi prompt & nhận phân tích NLU/công thức từ"| G
    S -->|"Lấy thông tin vi chất bổ sung từ"| SP

    classDef actor fill:#08427b,stroke:#052e56,color:#fff;
    classDef system fill:#1168bd,stroke:#0b4c8c,color:#fff;
    classDef external fill:#999999,stroke:#666666,color:#fff;
    class U,A actor;
    class S system;
    class G,SP,W external;
```

---

## 2. C4 - LEVEL 2: SƠ ĐỒ CONTAINER (CONTAINER DIAGRAM)

Sơ đồ này phân rã hệ thống thành các "Container" chạy độc lập (Web Server, Background Worker, Database, Trình duyệt Web).

```mermaid
graph LR
    subgraph Client_Side [Phía Người Dùng]
        Browser["Web Browser (SPA / Templates)<br>[HTML5, CSS, JS, Chart.js]<br>- Hiển thị UI Dashboard & Chat"]
    end

    subgraph Cloud_Server [Hạ Tầng Web Server / VPS]
        Proxy["Nginx Reverse Proxy<br>- SSL/TLS, Cân bằng tải, Phục vụ tĩnh"]
        
        App["Django Web Application Server<br>[Python, WSGI/Gunicorn]<br>- Xử lý nghiệp vụ chính<br>- API Endpoints & Core Logic"]
        
        Worker["Background Worker<br>[Cron Daemon / Celery]<br>- Chạy crawler hàng đêm<br>- ETL và làm sạch dữ liệu"]
        
        DB[("PostgreSQL Database<br>[PostgreSQL RDBMS]<br>- Lưu thông tin User, Dinh dưỡng,<br>Thực đơn, Chat & Metadata")]
    end

    subgraph External_Services [Dịch Vụ Ngoại Vi]
        Gemini["Google Gemini API<br>[gemini-2.5-flash]"]
        Spoon["Spoonacular API"]
    end

    %% Interactions
    Browser -->|"HTTPS (Port 443)"| Proxy
    Proxy -->|"Reverse Proxy (Port 8000)"| App
    App -->|"Django ORM"| DB
    Worker -->|"Django ORM"| DB
    App -->|"Outbound HTTPS"| Gemini
    App -->|"Outbound HTTPS"| Spoon
    Worker -->|"Web Scraping / HTTP"| External_Services

    classDef container fill:#438dd5,stroke:#3072b4,color:#fff;
    classDef db fill:#1168bd,stroke:#0b4c8c,color:#fff;
    classDef browser fill:#08427b,stroke:#052e56,color:#fff;
    classDef external fill:#9c27b0,stroke:#6a1b9a,color:#fff;
    
    class Proxy,App,Worker container;
    class DB db;
    class Browser browser;
    class Gemini,Spoon external;
```

---

## 3. C4 - LEVEL 3: SƠ ĐỒ THÀNH PHẦN (COMPONENT DIAGRAM)

Sơ đồ này đi sâu vào kiến trúc bên trong của Container **Django Web Application Server**, chỉ ra cách phân tách các lớp nghiệp vụ theo nguyên lý Clean Architecture.

```mermaid
graph TD
    %% Controllers & Views
    subgraph Presentation_Layer [Lớp Trình Bày - Presentation Layer]
        CV["Chat views & API Controller<br>[apps/chat/views.py]"]
        MV["Meal Plan views & API Controller<br>[apps/meal_plans/views.py]"]
        NV["Nutrition & Food views & API<br>[apps/nutrition/views.py]"]
        AV["Admin Dashboard views<br>[apps/admin_panel/views.py]"]
    end

    %% Business Services
    subgraph Application_Layer [Lớp Nghiệp Vụ - Application Service Layer]
        Orch["AI Orchestrator Service<br>[ai_orchestrator_service.py]<br>- Điều phối Hybrid AI"]
        
        Pers["Personalization Service<br>[personalization_service.py]<br>- Tính score S(u,f) & Rerank"]
        
        MealGen["Meal Plan Generator Service<br>[meal_plan_generator_service.py]<br>- Lên thực đơn tự động"]
        
        Parser["Ingredient Parser Service<br>[ingredient_parser_service.py]<br>- NLU trích xuất nguyên liệu"]
        
        ExtAPI["External API Adapter<br>[external_apis.py]<br>- Gọi Gemini/Spoon & Similarity Cache"]
    end

    %% Data Access (Django ORM)
    subgraph Infrastructure_Layer [Lớp Hạ Tầng Dữ Liệu - Infrastructure Layer]
        ORM["Django ORM Models"]
        DB[(PostgreSQL Database)]
    end

    %% Routing Flow
    CV --> Orch
    MV --> MealGen
    NV --> Parser
    AV --> Pers

    Orch --> Pers
    Orch --> ExtAPI
    MealGen --> Pers
    Parser --> ExtAPI

    Pers --> ORM
    MealGen --> ORM
    ExtAPI --> ORM
    ORM --> DB

    classDef layer fill:#f9f9f9,stroke:#333,stroke-dasharray: 5 5;
    classDef comp fill:#85b3dec,stroke:#2b6ba3,color:#000;
    classDef db fill:#1168bd,stroke:#0b4c8c,color:#fff;
    
    class CV,MV,NV,AV comp;
    class Orch,Pers,MealGen,Parser,ExtAPI comp;
    class DB db;
```

---

## 4. SƠ ĐỒ QUAN HỆ THỰC THỂ CƠ SỞ DỮ LIỆU (DATABASE ERD)

Dưới đây là sơ đồ ERD mô tả cấu trúc các bảng dữ liệu chính trong PostgreSQL và mối quan hệ giữa các phân hệ: **Users (Hồ sơ người dùng)**, **Nutrition (Dinh dưỡng & Thực phẩm)**, **Meal Plans (Thực đơn)**, và **Chat/AI**.

```mermaid
erDiagram
    %% User Module
    ACCOUNTS ||--|| USER_PROFILES : "has"
    ACCOUNTS ||--o{ USER_GOALS : "defines"
    ACCOUNTS ||--o{ USER_DISEASES : "has"
    ACCOUNTS ||--o{ USER_PREFERENCE_PROFILES : "owns"
    ACCOUNTS ||--o{ USER_FEEDBACK : "submits"

    %% Nutrition Module
    FOODS }|--|| FOOD_CATEGORIES : "belongs to"
    FOODS ||--o{ FOOD_INGREDIENTS : "contains"
    INGREDIENTS ||--o{ FOOD_INGREDIENTS : "part of"
    FOODS ||--o{ FOOD_PRICES : "tracks"
    INGREDIENTS ||--o{ INGREDIENT_PRICES : "tracks"

    %% Meal Plan Module
    ACCOUNTS ||--o{ MEAL_PLANS : "creates"
    MEAL_PLANS }|--|| FOODS : "includes"

    %% Chat & AI Module
    ACCOUNTS ||--o{ CHAT_SESSIONS : "starts"
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : "contains"
    CHAT_MESSAGES ||--o{ MESSAGE_INTENTS : "classified as"
    INTENTS ||--o{ MESSAGE_INTENTS : "defines"
    INTENTS ||--o{ PATTERNS : "trained by"
    CHAT_MESSAGES ||--o{ INTENT_EMBEDDINGS : "has vector"
    
    %% AI Recommendations
    ACCOUNTS ||--o{ AI_RECOMMENDATIONS : "receives"
    AI_RECOMMENDATIONS }|--|| FOODS : "recommends"

    ACCOUNTS {
        int id PK
        string username
        string email
        string role
        boolean is_active
    }

    USER_PROFILES {
        int id PK
        int account_id FK
        string name
        int age
        string gender
        float height
        float weight
        string activity_level
        float daily_calorie_target
        float budget_limit
    }

    USER_GOALS {
        int id PK
        int account_id FK
        string goal_type
        float target_value
    }

    USER_PREFERENCE_PROFILES {
        int id PK
        int account_id FK
        string preferred_categories
        string avoided_keywords
    }

    FOODS {
        int id PK
        string name
        string normalized_name
        int category_id FK
        float calories
        float protein
        float carbs
        float fat
        float fiber
        boolean is_diabetes_friendly
    }

    INGREDIENTS {
        int id PK
        string name
        string normalized_name
    }

    FOOD_INGREDIENTS {
        int id PK
        int food_id FK
        int ingredient_id FK
        float amount
        string unit
    }

    MEAL_PLANS {
        int id PK
        int account_id FK
        int food_id FK
        date date
        string meal_type
        float servings
    }

    CHAT_SESSIONS {
        int id PK
        int account_id FK
        string title
        timestamp created_at
    }

    CHAT_MESSAGES {
        int id PK
        int session_id FK
        string role
        text content
        timestamp created_at
    }

    MESSAGE_INTENTS {
        int id PK
        int message_id FK
        int intent_id FK
        float confidence
    }

    INTENTS {
        int id PK
        string name
        string description
    }

    AI_RECOMMENDATIONS {
        int id PK
        int account_id FK
        int food_id FK
        float score
        text reason
    }
```

---

## 5. LUỒNG DỮ LIỆU ĐIỂN HÌNH (DATA FLOW)
### Luồng Đề Xuất Thực Đơn & Cá Nhân Hóa (Meal Plan Generation Flow)

Sơ đồ tuần tự (Sequence Diagram) dưới đây mô tả cách các thành phần phần mềm tương tác với nhau khi người dùng gửi yêu cầu tạo thực đơn.

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng (Browser)
    participant MPV as Meal Plan View
    participant MPG as Meal Plan Generator
    participant PS as Personalization Service
    participant ORM as Django ORM & DB
    participant AI as AI Orchestrator (Fallback)

    User->>MPV: Yêu cầu tạo Thực đơn tuần mới
    MPV->>MPG: generate_meal_plan(account_id)
    MPG->>ORM: Lấy hồ sơ người dùng (UserProfile, UserGoal, UserDisease)
    ORM-->>MPG: Trả về context người dùng (Age, Weight, Disease: Tiểu đường)
    
    MPG->>ORM: Query danh sách món ăn ứng viên (Food Candidate Pool)
    ORM-->>MPG: Trả về 50 món ăn ngẫu nhiên phù hợp Calo nền
    
    loop Chấm điểm & Xếp hạng (Reranking)
        MPG->>PS: score_food_for_user(account, food)
        PS->>PS: Lọc bỏ món kỵ bệnh tiểu đường (Hard Constraint)
        PS->>PS: Tính điểm tối ưu S(u, f) dựa trên Calo, Giá tiền, Lịch sử ăn gần đây
        PS-->>MPG: Trả về PersonalizedScore (Điểm số & Lý do đề xuất)
    end
    
    MPG->>MPG: Sắp xếp theo score giảm dần & Chọn top món ăn cho từng bữa
    
    alt Số lượng ứng viên trong DB không đủ (Ví dụ thiếu món ăn sáng)
        MPG->>AI: generate_meal_plan_with_gemini(user_context)
        AI-->>MPG: Trả về danh sách món bổ sung (JSON)
        MPG->>ORM: Lưu món ăn mới crawl/sinh bởi AI vào DB
    end
    
    MPG->>ORM: Tạo & Lưu các bản ghi MealPlan mới
    MPG-->>MPV: Trả về kết quả thực đơn thành công
    MPV-->>User: Hiển thị thực đơn trực quan (Lịch biểu, Biểu đồ Calo)
```
