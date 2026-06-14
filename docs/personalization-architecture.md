# Kiến trúc Hệ thống Cá nhân hóa - Smart Home Chef (Tối giản)

Sơ đồ thể hiện luồng xử lý yêu cầu người dùng theo dạng pipeline (đường ống) tuần tự, từ khi nhận thông tin đầu vào đến khi trả về kết quả cá nhân hóa trên giao diện.

---

## 1. Sơ đồ luồng xử lý tối giản (Flowchart)

```mermaid
graph LR
    %% Style tối giản
    classDef client fill:#E3F2FD,stroke:#1E88E5,stroke-width:2px;
    classDef process fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px;
    classDef db fill:#FFF3E0,stroke:#FF9800,stroke-width:2px;
    classDef ai fill:#FCE4EC,stroke:#E91E63,stroke-width:2px;

    %% Các bước trong Pipeline
    A["1. Yêu cầu đầu vào<br>(Chat / Nguyên liệu)"]:::client
    B["2. Nhận diện ý định<br>(Intent Classifier)"]:::process
    C["3. Nạp hồ sơ sức khỏe<br>(User Context)"]:::process
    D["4. Tính điểm phù hợp<br>(Scoring Engine)"]:::process
    E{"CSDL có sẵn món?"}:::process
    
    F["5a. Phản hồi trực tiếp"]:::client
    G["5b. Gọi Gemini API<br>(Sinh món mới)"]:::ai
    
    DB[("PostgreSQL")]:::db

    %% Kết nối
    A --> B
    B --> C
    C --> D
    D --> E
    
    %% Ràng buộc Database
    C <-->|Lấy profile, bệnh lý| DB
    D <-->|Chấm điểm calo, dị ứng| DB
    
    %% Quyết định
    E -->|Có| F
    E -->|Không| G
    G -->|Tự động lưu món| DB
    G --> F
```

---

## 2. Giải thích 5 bước cốt lõi

1.  **Yêu cầu đầu vào:** Người dùng nhập nguyên liệu hiện có hoặc đặt câu hỏi yêu cầu thực đơn.
2.  **Nhận diện ý định:** Hệ thống phân tích xem người dùng muốn nấu ăn (Recipe) hay lập thực đơn (Meal Plan).
3.  **Nạp hồ sơ sức khỏe:** Lấy dữ liệu cá nhân trong PostgreSQL (bệnh nền, ngân sách, nhóm nguyên liệu dị ứng).
4.  **Tính điểm phù hợp (Scoring):** Chấm điểm các món ăn từ `0.0` đến `1.0` (Ưu tiên món hợp calo/bệnh lý, loại bỏ món dị ứng).
5.  **Trả kết quả:** 
    *   Nếu CSDL có sẵn món phù hợp $\rightarrow$ Trả kết quả ngay.
    *   Nếu thiếu món $\rightarrow$ Gọi **Gemini API** sinh món mới, lưu vào CSDL rồi gửi cho người dùng.
