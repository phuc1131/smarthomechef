# Smart Home Chef

Smart Home Chef là một ứng dụng Django cho lập thực đơn, tư vấn dinh dưỡng, gợi ý món ăn, tạo công thức nấu ăn và quản trị dữ liệu thực phẩm. Dự án hiện tại không chỉ phụ thuộc vào AI API bên ngoài mà có thêm một lớp AI nội bộ có thể học từ dữ liệu trong database, rồi dùng Gemini làm fallback khi cần sinh ngôn ngữ tự do hoặc khi dữ liệu cục bộ chưa đủ.

## Tổng Quan

Dự án này đang đi theo hướng kết hợp giữa:

- Django feature-based architecture: mỗi domain chính nằm trong một app riêng.
- Legacy compatibility layer: `app/` vẫn còn tồn tại để giữ các route, service và import cũ hoạt động ổn định trong quá trình chuyển đổi.
- Internal learning AI: dữ liệu hội thoại, pattern, intent và recommendation log được lưu vào DB để train và cải thiện dần.
- External generation fallback: Gemini được dùng cho sinh văn bản, biến thể công thức, hoặc các trường hợp mà DB/rule engine chưa đủ.

## Tính Năng Chính

- Gợi ý món ăn theo sở thích, mục tiêu sức khỏe và lịch sử ăn gần đây.
- Lập meal plan theo ngày, mục tiêu calories, bệnh nền và ngân sách.
- Chat hỗ trợ hỏi đáp về dinh dưỡng, món ăn, nguyên liệu và shopping list.
- Gợi ý công thức từ nguyên liệu có sẵn.
- Crawler/seed/diagnostic tools để nạp dữ liệu và kiểm tra hệ thống.
- Hệ AI nội bộ có thể học từ `Intent`, `Pattern`, `MessageIntent` và `ModelMetadata`.

## Kiến Trúc Hiện Tại

### 1. Lớp giao diện và route

- `smart_chef/` chứa cấu hình Django gốc: settings, urls, wsgi, template và static.
- `app/` chứa một lớp compatibility cũ, hiện vẫn giữ views và services đang được dùng bởi hệ thống.
- `apps/` là nơi tập trung các feature app theo domain.

### 2. Lớp nghiệp vụ

- `app/services/` chứa các service quan trọng như phân loại intent, cá nhân hóa, tạo meal plan, sinh recipe, parse nguyên liệu, feedback sức khỏe và kết nối AI ngoài.
- `apps/*/models.py` chứa dữ liệu lõi của từng domain.
- `apps/core_models/ai_learning_models.py` là nơi lưu các model phục vụ học máy nhẹ, theo dõi recommendation và metadata mô hình.

### 3. Lớp AI nội bộ

AI nội bộ hiện tại gồm ba phần chính:

- Phân loại intent bằng rule + dữ liệu huấn luyện từ DB.
- Cá nhân hóa score cho food/recommendation dựa trên profile, goal, disease, feedback và lịch sử.
- Lưu artifact mô hình ở `artifacts/ai_models/intent_classifier.json`.

### 4. Lớp fallback AI ngoài

- Gemini chỉ là lớp dự phòng cho chat sinh ngôn ngữ tự do, meal plan fallback, recipe generation và một số tác vụ parse/nội dung nâng cao.
- Khi DB có đủ dữ liệu, hệ thống ưu tiên trả lời từ dữ liệu nội bộ trước.

## Yêu Cầu Môi Trường

- Windows PowerShell hoặc môi trường tương đương.
- Python 3.11+.
- Virtual environment `.venv`.
- Database mặc định có thể là SQLite, nhưng project cũng hỗ trợ cấu hình qua `DATABASE_URL` hoặc biến `DB_*`.
- Nếu dùng AI ngoài, cần cấu hình `GEMINI_API_KEY`.

## Cài Đặt Nhanh

> Repo hiện không dùng `requirements.txt`; dependency nền tảng đang được khai trong `pyproject.toml` và project còn phụ thuộc vào các package Django khác mà môi trường `.venv` của bạn phải có sẵn.

```powershell
python -m venv .venv
& ".venv/Scripts/Activate.ps1"
pip install django django-allauth dj-database-url google-genai psycopg2-binary schedule whitenoise
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Nếu bạn đang dùng database khác SQLite, cấu hình thêm `.env` trước khi chạy migrate.

## Biến Môi Trường Quan Trọng

Ví dụ `.env`:

```env
SECRET_KEY=your-secret
DEBUG=true
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgres://user:password@localhost:5432/smartchef
GEMINI_API_KEY=your-gemini-key
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

Các biến quan trọng khác mà project đọc:

- `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`
- `REQUIRE_AUTH`
- `CSRF_TRUSTED_EXTRA_ORIGINS`

## Chạy Hệ Thống

```powershell
& ".venv/Scripts/Activate.ps1"
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Một số lệnh hữu ích khác:

```powershell
& ".venv/Scripts/Activate.ps1"
python manage.py showmigrations
python manage.py migrate --plan
python manage.py createsuperuser
```

## AI Và Dữ Liệu Học

### Dữ liệu train hiện tại

- `apps/chat/models.py`: `Intent`, `Pattern`, `ChatSession`, `ChatMessage`, `MessageIntent`, `IntentEmbedding`.
- `apps/core_models/ai_learning_models.py`: `IntentPattern`, `RecommendationLog`, `ModelMetadata` và các model học AI liên quan.
- `tools/seeding/seed_data_consolidated.py`: seed canonical intents, patterns, foods và labeled message samples.

### Service AI chính

- `app/services/model_training_service.py`: train intent classifier từ dữ liệu trong DB.
- `app/services/ai_orchestrator_service.py`: điểm vào tập trung cho phân loại intent, health report và capability discovery.
- `app/services/personalization_service.py`: chấm điểm món ăn theo hồ sơ người dùng.
- `app/services/meal_plan_generator_service.py`: tạo meal plan và rerank theo personal profile khi có account.
- `app/services/recipe_generator_service.py`: gợi ý recipe từ nguyên liệu, có thể rerank theo account.
- `app/services/external_apis.py`: lớp tích hợp Gemini và cache kết quả AI.

### Artifact mô hình

- Intent classifier hiện lưu ở `artifacts/ai_models/intent_classifier.json`.
- Trạng thái mô hình có thể kiểm tra bằng `tools/diagnostics/check_ai_status.py`.

## Lệnh Seed Và Kiểm Tra AI

```powershell
& ".venv/Scripts/Activate.ps1"
python tools/seeding/seed_data_consolidated.py
python tools/diagnostics/check_ai_status.py
```

Nếu muốn chạy riêng từng phần seed:

```powershell
& ".venv/Scripts/Activate.ps1"
python tools/seeding/seed_data_consolidated.py --foods
python tools/seeding/seed_data_consolidated.py --intents
python tools/seeding/seed_data_consolidated.py --patterns
```

## Cây Thư Mục Chi Tiết

```text
.
├── README.md
├── manage.py
├── pyproject.toml
├── package.json
├── pytest.ini
├── db.sqlite3
├── .env
├── app/
│   ├── __init__.py
│   ├── admin.py
│   ├── api_recipe_rating.py
│   ├── auth_views.py
│   ├── chat_views.py
│   ├── config.py
│   ├── context_processors.py
│   ├── dashboard_views.py
│   ├── food_views.py
│   ├── meal_plan_views.py
│   ├── models.py
│   ├── nutrition_views.py
│   ├── oauth_views.py
│   ├── profile_views.py
│   ├── utils.py
│   ├── features/
│   │   └── user_panel/
│   │       └── views.py
│   ├── management/
│   │   └── commands/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_delete_chatmessage_remove_mealplan_food_and_more.py
│   │   ├── 0003_mealplan_add_account.py
│   │   └── 0004_remove_mealplan_food_remove_mealplan_account_and_more.py
│   └── services/
│       ├── ai_orchestrator_service.py
│       ├── chat_text_service.py
│       ├── external_apis.py
│       ├── food_classifier_service.py
│       ├── food_data_service.py
│       ├── grocery_list_service.py
│       ├── health_feedback_service.py
│       ├── ingredient_parser_service.py
│       ├── ingredient_price_service.py
│       ├── meal_plan_generator_service.py
│       ├── model_training_service.py
│       ├── nutrition_data_service.py
│       ├── personalization_service.py
│       ├── recipe_generator_service.py
│       ├── recipe_generator_service_patch.py
│       └── recipe_variations_service.py
├── apps/
│   ├── admin_panel/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── management/
│   │   └── migrations/
│   ├── chat/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── enhanced_chat_models.py
│   │   ├── management/
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── core_models/
│   │   ├── admin.py
│   │   ├── ai_learning_models.py
│   │   ├── api_hub.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── signals.py
│   │   └── migrations/
│   ├── meal_plans/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── constants.py
│   │   ├── management/
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── nutrition/
│   │   ├── admin.py
│   │   ├── admin_models.py
│   │   ├── apps.py
│   │   ├── food_management_models.py
│   │   ├── management/
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── urls.py
│   │   └── views.py
│   └── users/
│       ├── admin.py
│       ├── allauth_adapter.py
│       ├── apps.py
│       ├── auth_backend.py
│       ├── auth_utils.py
│       ├── forms.py
│       ├── management/
│       ├── migrations/
│       ├── models.py
│       ├── personalization_models.py
│       ├── urls.py
│       └── views.py
├── artifacts/
│   └── ai_models/
│       └── intent_classifier.json
├── database/
│   └── schema_current.sql
├── docs/
│   ├── architecture.md
│   ├── ai-model.md
│   ├── CRAWL_WINMART.md
│   ├── database-schema.md
│   ├── GOOGLE_OAUTH_SETUP.md
│   ├── MEAL_PLAN_CHAT_FIXES.md
│   ├── PASSWORD_CHANGE_RESET_FEATURES.md
│   ├── style-guide.md
│   ├── usecase.md
│   ├── usecase-analysis.md
│   ├── usecase-specification-django-json-data.md
│   └── reports/
├── services/
│   ├── chat_text_service.py
│   ├── external_apis.py
│   ├── food_data_service.py
│   ├── grocery_list_service.py
│   ├── health_feedback_service.py
│   ├── ingredient_parser_service.py
│   ├── recipe_generator_service.py
│   └── recipe_variations_service.py
├── smart_chef/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── templates/
│   └── static/
├── tests/
│   ├── test_accounts_api.py
│   ├── test_accounts_simple.py
│   ├── test_api_endpoint.py
│   ├── test_food_classifier.py
│   ├── test_gemini_config.py
│   ├── test_grocery_list_service.py
│   ├── test_ingredient_parser.py
│   ├── test_recipe_api.py
│   ├── test_recipe_generator.py
│   ├── test_recipe_variations.py
│   └── test_shopping_list_api.py
├── tools/
│   ├── diagnostics/
│   │   ├── check_ai_status.py
│   │   ├── check_chat.py
│   │   └── check_runtime_tables.py
│   ├── maintenance/
│   │   └── backfill_personalization_data.py
│   ├── seeding/
│   │   ├── seed_data.py
│   │   └── seed_data_consolidated.py
│   ├── validation/
│   │   └── legacy/
│   └── database/
├── check_database_status.py
├── check_tables.py
├── cleanup_migration_history.py
├── cleanup_migration_history2.py
├── create_superuser.py
├── fix_all_ids.py
├── reset_ids.py
├── seed_vietnamese_foods.py
├── setup_google_oauth.py
├── test_execution_summary.py
├── test_recipe_gemini.py
├── test_recipe_generation_mocked.py
├── verify_ingredients_crawl.py
├── verify_renumbering.py
└── VIETNAMESE_FOODS_IMPORT.md
```

## Các Khu Vực Nên Quan Tâm Khi Phát Triển

- `app/services/model_training_service.py`: nơi train intent model từ dữ liệu thật.
- `app/services/personalization_service.py`: nơi tính điểm và rerank theo account.
- `app/features/user_panel/views.py`: luồng user-facing chat/recommendation.
- `tools/seeding/seed_data_consolidated.py`: nguồn seed thống nhất cho dữ liệu học.
- `tools/diagnostics/check_ai_status.py`: kiểm tra AI runtime end-to-end.
- `apps/chat/models.py`: backbone cho intent learning và chat history.
- `apps/core_models/ai_learning_models.py`: lưu model metadata và log học AI.

## Lưu Ý Phát Triển

- Ưu tiên import model từ `apps.*` thay vì quay lại model cũ trong `app.models`.
- Trước khi đụng vào model/migration, chạy `python manage.py check`.
- Khi thêm logic AI mới, ưu tiên flow DB-first rồi mới fallback sang Gemini.
- Khi seed dữ liệu học, luôn bảo đảm intent/pattern/message sample khớp tên canonical.
- Với recommendation, giữ rerank cá nhân hóa ở service layer, không dồn hết vào view.

## Kiểm Tra Nhanh Sau Khi Thay Đổi

```powershell
& ".venv/Scripts/Activate.ps1"
python manage.py check
python tools/diagnostics/check_ai_status.py
python tools/seeding/seed_data_consolidated.py
```

## Ghi Chú Cuối

Nếu bạn muốn, README này có thể được tách tiếp thành 2 phần riêng:

1. README cho người dùng cuối, ngắn và dễ chạy.
2. README kỹ thuật nội bộ, tập trung vào kiến trúc AI, seed, training và debugging.
