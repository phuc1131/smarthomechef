# Database Schema

Tài liệu này ghi lại các bảng hiện có trong CSDL của dự án tại thời điểm hiện tại, dựa trên metadata Django và bảng đang tồn tại trong DB.

## Tổng Quan

Các bảng hiện có:

- `django_admin_log`
- `auth_permission`
- `auth_group`
- `auth_user`
- `django_content_type`
- `django_session`
- `users`
- `user_profiles`
- `user_goals`
- `user_feedback`
- `user_preference_profiles`
- `intents`
- `patterns`
- `chat_sessions`
- `chat_messages`
- `chat_summaries`
- `conversation_states`
- `message_intents`
- `intent_embeddings`
- `chat_response_caches`
- `foods`
- `ingredients`
- `food_ingredients`
- `food_details`
- `food_recipes`
- `nutrition_logs`
- `daily_nutrition_summary`
- `recipe_translations`
- `text_translations`
- `meal_plans`
- `meal_type_configs`
- `ai_recommendations`
- `search_events`

## Đối Chiếu Theo Yêu Cầu

Nội dung schema bạn vừa đưa đã được bao phủ gần như đầy đủ trong tài liệu này. Phần thiếu quan trọng nhất trước đó là giá cho thực phẩm sau crawl, và hiện đã được bổ sung bằng nhóm `food_prices` / `food_price_history` cùng các bảng crawl `crawl_sources` / `crawl_runs` / `crawl_items`.

Tóm tắt đối chiếu nhanh:

- Nhóm hệ thống Django: đã có `django_admin_log`, `auth_permission`, `auth_group`, `auth_user`, `django_content_type`, `django_session`.
- Nhóm user domain: đã có `users`, `user_profiles`, `user_goals`, `user_feedback`, `user_preference_profiles`.
- Nhóm chat & AI: đã có `intents`, `patterns`, `chat_sessions`, `chat_messages`, `chat_summaries`, `conversation_states`, `message_intents`, `intent_embeddings`, `chat_response_caches`.
- Nhóm nutrition & meal plan: đã có `foods`, `ingredients`, `food_ingredients`, `food_details`, `food_recipes`, `nutrition_logs`, `daily_nutrition_summary`, `meal_plans`, `meal_type_configs`, `recipe_translations`, `text_translations`.
- Nhóm core & analytics: đã có `ai_recommendations`, `search_events`.
- Nhóm mở rộng lý tưởng: đã bổ sung `ingredient_prices`, `ingredient_price_history`, `food_prices`, `food_price_history`, `crawl_sources`, `crawl_runs`, `crawl_items`, `diseases`, `disease_nutrition_rules`, `food_verification_queue`.

Kết luận: dữ liệu yêu cầu là đủ để điền vào schema, và phần tích hợp hiện tại đã phản ánh cả schema đang dùng lẫn schema lý tưởng mở rộng.

## Django System Tables

Các bảng này là bảng hệ thống do Django tạo sẵn. Chúng không chứa dữ liệu nghiệp vụ chính như món ăn hay công thức, mà phục vụ cho đăng nhập, phân quyền, quản trị và lưu trạng thái phiên làm việc.

### `django_admin_log`
Model: `admin.LogEntry`

Mục đích: Lưu lịch sử thao tác trong trang quản trị, để biết ai đã tạo, sửa hoặc xóa dữ liệu nào.
Mục đích sử dụng: Theo dõi toàn bộ thao tác quản trị để audit và truy vết khi có sự cố.

Fields:
- `id` - AutoField
- `action_time` - DateTimeField
- `user_id` - ForeignKey to auth user
- `content_type_id` - ForeignKey to content types, nullable
- `object_id` - TextField, nullable
- `object_repr` - CharField
- `action_flag` - PositiveSmallIntegerField
- `change_message` - TextField

### `auth_permission`
Model: `auth.Permission`

Mục đích: Lưu các quyền truy cập như xem, thêm, sửa, xóa dữ liệu cho từng bảng/model.
Mục đích sử dụng: Phân quyền cho người dùng và nhóm quyền theo từng chức năng của hệ thống.

Fields:
- `id` - AutoField
- `name` - CharField
- `content_type_id` - ForeignKey to content types
- `codename` - CharField

### `auth_group`
Model: `auth.Group`

Mục đích: Lưu nhóm quyền, ví dụ nhóm quản trị viên hoặc nhóm nhân viên, để gán quyền nhanh hơn.
Mục đích sử dụng: Gom nhiều quyền thành một vai trò để quản lý phân quyền dễ hơn.

Fields:
- `id` - AutoField
- `name` - CharField

### `auth_user`
Model: `auth.User`

Mục đích: Lưu tài khoản người dùng mặc định của Django, chủ yếu dùng cho hệ thống admin và các chức năng xác thực chuẩn của Django.
Mục đích sử dụng: Cung cấp tài khoản đăng nhập mặc định cho các chức năng hệ thống của Django.

Fields:
- `id` - AutoField
- `password` - CharField
- `last_login` - DateTimeField, nullable
- `is_superuser` - BooleanField
- `username` - CharField
- `first_name` - CharField
- `last_name` - CharField
- `email` - CharField
- `is_staff` - BooleanField
- `is_active` - BooleanField
- `date_joined` - DateTimeField

### `django_content_type`
Model: `contenttypes.ContentType`

Mục đích: Lưu thông tin nhận diện từng bảng/model trong hệ thống, để Django biết bảng nào đang được thao tác, phân quyền hoặc ghi log.
Mục đích sử dụng: Làm lớp định danh cho model để phục vụ admin, permission và generic relation.

Fields:
- `id` - AutoField
- `app_label` - CharField
- `model` - CharField

### `django_session`
Model: `sessions.Session`

Mục đích: Lưu phiên đăng nhập, giúp hệ thống nhớ người dùng đang đăng nhập mà không cần nhập lại ở mỗi request.
Mục đích sử dụng: Giữ trạng thái đăng nhập tạm thời giữa các request của người dùng.

Fields:
- `session_key` - CharField
- `session_data` - TextField
- `expire_date` - DateTimeField

## User Domain

### `users`
Model: `users.Account`

Mục đích sử dụng: Lưu tài khoản chính của người dùng trong hệ thống.

Fields:
- `id` - BigAutoField
- `username` - CharField
- `email` - CharField
- `password_hash` - TextField
- `role` - CharField
- `is_active` - BooleanField
- `created_at` - DateTimeField

Notes:
- Đây là bảng tài khoản custom của hệ thống.
- `password_hash` phải là hash hợp lệ do Django tạo, không dùng plaintext.

### `user_profiles`
Model: `users.UserProfile`

Mục đích sử dụng: Lưu thông tin cá nhân, chỉ số cơ thể và mục tiêu sức khỏe của người dùng.

Fields:
- `id` - BigAutoField
- `account_id` - OneToOneField, nullable
- `name` - CharField
- `age` - IntegerField, nullable
- `weight` - DecimalField, nullable
- `height` - DecimalField, nullable
- `gender` - CharField, nullable
- `health_goal` - TextField, nullable
- `medical_conditions` - TextField, nullable
- `dietary_preferences` - TextField, nullable
- `activity_level` - CharField, nullable
- `bmi` - FloatField, nullable
- `daily_calorie_target` - IntegerField, nullable
- `created_at` - DateTimeField
- `updated_at` - DateTimeField

### `user_goals`
Model: `users.UserGoal`

Mục đích sử dụng: Lưu các mục tiêu dinh dưỡng hoặc mục tiêu thể chất mà người dùng đang theo đuổi.

Fields:
- `id` - BigAutoField
- `account_id` - ForeignKey, nullable
- `goal_type` - CharField, nullable
- `target_weight` - FloatField, nullable
- `daily_calorie_target` - IntegerField, nullable
- `created_at` - DateTimeField

### `user_feedback`
Model: `users.UserFeedback`

Mục đích sử dụng: Lưu phản hồi và đánh giá của người dùng về món ăn, công thức hoặc gợi ý.

Fields:
- `id` - BigAutoField
- `account_id` - ForeignKey, nullable
- `food_id` - ForeignKey, nullable
- `rating` - IntegerField, nullable
- `liked` - BooleanField, nullable
- `created_at` - DateTimeField

### `user_preference_profiles`
Model: `users.UserPreferenceProfile`

Mục đích sử dụng: Tổng hợp sở thích ăn uống để AI gợi ý món phù hợp hơn cho từng người.

Fields:
- `id` - BigAutoField
- `account_id` - OneToOneField
- `healthy_score` - FloatField
- `unhealthy_score` - FloatField
- `preferred_categories` - JSONField, nullable
- `preferred_keywords` - JSONField, nullable
- `avoided_keywords` - JSONField, nullable
- `latest_summary` - JSONField, nullable
- `updated_at` - DateTimeField

## Chat / AI Domain

### `intents`
Model: `chat.Intent`

Mục đích sử dụng: Lưu danh sách ý định hội thoại mà chatbot có thể nhận diện.

Fields:
- `id` - BigAutoField
- `name` - CharField, nullable
- `description` - TextField, nullable
- `required_fields` - JSONField, nullable
- `topic` - CharField, nullable

### `patterns`
Model: `chat.Pattern`

Mục đích sử dụng: Lưu các câu mẫu giúp huấn luyện hoặc nhận diện intent trong chat.

Fields:
- `id` - BigAutoField
- `intent_id` - ForeignKey, nullable
- `text` - TextField

### `chat_sessions`
Model: `chat.ChatSession`

Mục đích sử dụng: Lưu từng phiên trò chuyện riêng biệt của người dùng với AI.

Fields:
- `id` - BigAutoField
- `account_id` - ForeignKey, nullable
- `title` - CharField, nullable
- `created_at` - DateTimeField

### `chat_messages`
Model: `chat.ChatMessage`

Mục đích sử dụng: Lưu nội dung từng tin nhắn trong một phiên chat.

Fields:
- `id` - BigAutoField
- `session_id` - ForeignKey, nullable
- `role` - CharField
- `content` - TextField
- `created_at` - DateTimeField

### `chat_summaries`
Model: `chat.ChatSummary`

Mục đích sử dụng: Lưu bản tóm tắt ngắn của một phiên chat để đọc lại nhanh.

Fields:
- `id` - BigAutoField
- `session_id` - ForeignKey, nullable
- `summary` - TextField, nullable
- `created_at` - DateTimeField

### `conversation_states`
Model: `chat.ConversationState`

Mục đích sử dụng: Lưu trạng thái hội thoại đang dở để chatbot biết còn thiếu thông tin gì.

Fields:
- `id` - BigAutoField
- `account_id` - ForeignKey, nullable
- `missing_fields` - JSONField, nullable
- `ask_count` - IntegerField
- `updated_at` - DateTimeField
- `current_intent_id` - IntegerField, nullable
- `filled_fields` - JSONField, nullable

### `message_intents`
Model: `chat.MessageIntent`

Mục đích sử dụng: Gắn intent được dự đoán cho từng tin nhắn cùng mức độ tin cậy.

Fields:
- `id` - BigAutoField
- `message_id` - ForeignKey, nullable
- `intent_id` - ForeignKey, nullable
- `confidence` - FloatField, nullable

### `intent_embeddings`
Model: `chat.IntentEmbedding`

Mục đích sử dụng: Lưu vector embedding cho intent hoặc pattern để so khớp ngữ nghĩa nhanh hơn.

Fields:
- `id` - BigAutoField
- `message_id` - OneToOneField, nullable
- `pattern_id` - OneToOneField, nullable
- `intent_name` - CharField, nullable
- `embedding_vector` - JSONField
- `source_type` - CharField
- `confidence` - FloatField, nullable
- `created_at` - DateTimeField
- `updated_at` - DateTimeField

### `chat_response_caches`
Model: `chat.ChatResponseCache`

Mục đích sử dụng: Lưu phản hồi AI đã sinh sẵn để tái sử dụng, giảm chi phí gọi API.

Fields:
- `id` - BigAutoField
- `account_id` - ForeignKey, nullable
- `normalized_query` - TextField
- `original_query` - TextField
- `gemini_response` - TextField
- `source_intent` - CharField, nullable
- `usage_count` - IntegerField
- `created_at` - DateTimeField
- `last_used_at` - DateTimeField, nullable

## Nutrition Domain

### `foods`
Model: `nutrition.Food`

Mục đích sử dụng: Lưu danh mục thực phẩm và chỉ số dinh dưỡng cơ bản của từng món.

Fields:
- `id` - BigAutoField
- `name` - CharField
- `category` - CharField, nullable
- `calories` - DecimalField, nullable
- `protein` - DecimalField, nullable
- `carbs` - DecimalField, nullable
- `fat` - DecimalField, nullable
- `fiber` - DecimalField, nullable
- `serving_size` - CharField, nullable
- `description` - TextField, nullable
- `is_vegetarian` - BooleanField
- `is_diabetes_friendly` - BooleanField
- `is_weight_loss_friendly` - BooleanField
- `image_url` - TextField, nullable
- `created_at` - DateTimeField

### `ingredients`
Model: `nutrition.Ingredient`

Mục đích sử dụng: Lưu danh sách nguyên liệu thành phần dùng để ghép món ăn và công thức.

Fields:
- `id` - BigAutoField
- `name` - CharField, nullable

### `food_ingredients`
Model: `nutrition.FoodIngredient`

Mục đích sử dụng: Liên kết món ăn với nguyên liệu và lượng nguyên liệu sử dụng.

Fields:
- `id` - BigAutoField
- `food_id` - ForeignKey
- `ingredient_id` - ForeignKey
- `quantity` - FloatField, nullable

### `food_details`
Model: `nutrition.FoodDetail`

Mục đích sử dụng: Lưu thông tin dinh dưỡng mở rộng như vitamin, khoáng chất và chỉ số chi tiết.

Fields:
- `food_id` - OneToOneField
- `sugar` - FloatField, nullable
- `sodium` - FloatField, nullable
- `cholesterol` - FloatField, nullable
- `vitamin_a` - FloatField, nullable
- `vitamin_c` - FloatField, nullable
- `calcium` - FloatField, nullable
- `iron` - FloatField, nullable

### `food_recipes`
Model: `nutrition.Recipe`

Mục đích sử dụng: Lưu công thức nấu ăn gắn với từng món thực phẩm.

Fields:
- `id` - BigAutoField
- `food_id` - OneToOneField
- `external_id` - IntegerField, nullable
- `title` - CharField
- `summary` - TextField, nullable
- `source_url` - CharField, nullable
- `image_url` - TextField, nullable
- `ready_in_minutes` - IntegerField, nullable
- `servings` - FloatField, nullable
- `instructions` - TextField, nullable
- `ingredients` - JSONField, nullable
- `analyzed_instructions` - JSONField, nullable
- `nutrition` - JSONField, nullable
- `source_name` - CharField, nullable
- `created_at` - DateTimeField
- `updated_at` - DateTimeField

### `nutrition_logs`
Model: `nutrition.NutritionLog`

Mục đích sử dụng: Lưu nhật ký ăn uống hằng ngày của người dùng.

Fields:
- `id` - BigAutoField
- `account_id` - ForeignKey, nullable
- `food_id` - ForeignKey
- `date` - DateField
- `meal_type` - CharField
- `servings` - FloatField
- `total_calories` - FloatField, nullable
- `total_protein` - FloatField, nullable
- `total_carbs` - FloatField, nullable
- `total_fat` - FloatField, nullable
- `created_at` - DateTimeField

### `daily_nutrition_summary`
Model: `nutrition.DailyNutritionSummary`

Mục đích sử dụng: Lưu bảng tổng hợp dinh dưỡng theo ngày để xem nhanh và báo cáo.

Fields:
- `id` - BigAutoField
- `account_id` - ForeignKey, nullable
- `date` - DateField, nullable
- `total_calories` - FloatField, nullable
- `total_protein` - FloatField, nullable
- `total_carbs` - FloatField, nullable
- `total_fat` - FloatField, nullable

### `recipe_translations`
Model: `nutrition.RecipeTranslation`

Mục đích sử dụng: Lưu bản dịch công thức nấu ăn từ các nguồn bên ngoài.

Fields:
- `id` - BigAutoField
- `source_recipe_id` - CharField
- `source_api` - CharField
- `original_title` - TextField
- `translated_title` - TextField, nullable
- `translated_payload` - JSONField, nullable
- `created_at` - DateTimeField

### `text_translations`
Model: `nutrition.TextTranslation`

Mục đích sử dụng: Lưu các đoạn văn bản đã dịch để tái sử dụng và tránh dịch lại nhiều lần.

Fields:
- `id` - BigAutoField
- `original_text` - TextField
- `translated_text` - TextField
- `text_type` - CharField
- `source_context` - CharField, nullable
- `created_at` - DateTimeField

## Meal Plan Domain

### `meal_plans`
Model: `meal_plans.MealPlan`

Mục đích sử dụng: Lưu kế hoạch bữa ăn theo ngày hoặc theo từng bữa.

Fields:
- `id` - BigAutoField
- `account_id` - ForeignKey, nullable
- `food_id` - ForeignKey
- `date` - TextField
- `meal_type` - CharField
- `servings` - DecimalField
- `notes` - TextField, nullable
- `created_at` - DateTimeField

### `meal_type_configs`
Model: `meal_plans.MealTypeConfig`

Mục đích sử dụng: Lưu cấu hình các loại bữa ăn như sáng, trưa, tối, phụ.

Fields:
- `id` - BigAutoField
- `meal_type` - CharField
- `label` - CharField
- `badge_class` - CharField
- `sort_order` - IntegerField
- `is_active` - BooleanField

## Core Models

### `ai_recommendations`
Model: `core_models.AIRecommendation`

Mục đích sử dụng: Lưu gợi ý do AI tạo ra cho từng người dùng.

Fields:
- `id` - BigAutoField
- `account_id` - ForeignKey, nullable
- `food_id` - ForeignKey, nullable
- `reason` - TextField, nullable
- `score` - FloatField, nullable
- `created_at` - DateTimeField

### `search_events`
Model: `core_models.SearchEvent`

Mục đích sử dụng: Lưu lịch sử tìm kiếm để phân tích hành vi và cải thiện gợi ý.

Fields:
- `id` - BigAutoField
- `account_id` - ForeignKey, nullable
- `query_text` - TextField
- `normalized_query` - TextField, nullable
- `source` - CharField
- `result_count` - IntegerField
- `clicked_food_id` - ForeignKey, nullable
- `metadata` - JSONField, nullable
- `created_at` - DateTimeField

## Ideal Schema Integration

Phần này ghép bộ bảng lý tưởng mà bạn đưa vào với schema hiện tại của dự án sao cho không xung đột. Nguyên tắc là: giữ bảng đang có nếu đã dùng trong code, chỉ bổ sung cột hoặc map tên bảng tương đương, không tạo thêm bảng trùng chức năng.

### 1. Bảng nên giữ nguyên và mở rộng

Các bảng hiện tại nên được giữ lại vì đang được code sử dụng trực tiếp:

- `users`  
	Dùng cho tài khoản chính của hệ thống.
- `user_profiles`  
	Dùng cho hồ sơ cá nhân và mục tiêu dinh dưỡng.
- `user_goals`  
	Dùng cho các mục tiêu của người dùng.
- `user_feedback`  
	Dùng cho phản hồi món ăn/gợi ý.
- `user_preference_profiles`  
	Dùng cho hồ sơ sở thích đã tổng hợp.
- `intents`, `patterns`, `chat_sessions`, `chat_messages`, `chat_summaries`, `conversation_states`, `message_intents`, `intent_embeddings`, `chat_response_caches`  
	Dùng cho chat AI và NLU.
- `foods`, `ingredients`, `food_ingredients`, `food_details`, `food_recipes`, `nutrition_logs`, `daily_nutrition_summary`, `recipe_translations`, `text_translations`  
	Dùng cho thực phẩm, dinh dưỡng và công thức.
- `meal_plans`, `meal_type_configs`  
	Dùng cho kế hoạch bữa ăn.
- `ai_recommendations`, `search_events`  
	Dùng cho gợi ý AI và theo dõi hành vi.

### 2. Bảng lý tưởng cần map vào bảng hiện tại

| Schema lý tưởng | Bảng hiện tại nên dùng | Ghi chú |
|---|---|---|
| `user_budgets` | `user_budget_logs` hoặc thêm model riêng vào `users` | Nếu cần ngân sách theo ngày/tháng, nên thêm bảng riêng thay vì nhét vào `user_goals`. |
| `user_behavior_profiles` | `user_preference_profiles` / `user_profiles` | Nên gộp vào hồ sơ sở thích hiện có để tránh trùng dữ liệu. |
| `user_health_goals` | `user_goals` | Nếu muốn nhiều loại mục tiêu, thêm `goal_type`, `target_calories`, `target_macros`. |
| `food_categories` | `category` trong `foods` hoặc tạo bảng mới nếu cần danh mục chuẩn | Hiện `foods.category` đang đủ dùng; chỉ tạo bảng riêng nếu cần thống kê chặt chẽ. |
| `recipes` | `food_recipes` / `nutrition.Recipe` | Đây là bảng công thức hiện có, nên mở rộng thêm nếu thiếu cột. |
| `recipe_ingredients` | `food_ingredients` hoặc tạo bảng trung gian riêng cho recipe | Nếu muốn công thức có nguyên liệu riêng, nên tách bảng trung gian theo recipe. |
| `meal_recommendations` | `ai_recommendations` | Dùng chung cho gợi ý AI, thêm trường `recommendation_type` nếu cần phân loại. |
| `user_feedback_food` | `user_feedback` | Có thể thêm cột `feedback_type='food'`. |
| `user_feedback_recommendation` | `user_feedback` | Có thể thêm cột `feedback_type='recommendation'`. |
| `food_embeddings` | `intent_embeddings` không nên dùng chung | Nên tạo bảng riêng nếu cần embedding cho food; không dùng chung với intent vì khác mục đích. |
| `food_verification_queue` | Tạo bảng riêng trong `core_models` hoặc `admin_panel` | Dùng cho quy trình duyệt món ăn mới. |
| `audit_logs` | `core_models_audit_log` hoặc `core_models.AuditLog` | Nên giữ log riêng cho quản trị hệ thống. |
| `admin_settings` | `core_models_system_metric` không phù hợp | Nên tạo bảng config riêng, không dùng metric để lưu setting. |
| `system_metrics` | `core_models_system_metric` | Đây là map phù hợp nhất. |

### 3. Cách tránh xung đột khi tích hợp

1. Không tạo bảng mới nếu bảng hiện tại đã có chức năng tương đương.
2. Nếu cần thêm trường, dùng migration để `ADD COLUMN` thay vì tạo bảng mới.
3. Nếu muốn đổi tên bảng, chỉ làm khi toàn bộ code đã chuyển sang tên mới.
4. Với dữ liệu nhiều loại, ưu tiên thêm `type`, `source`, `status` thay vì tách quá nhiều bảng nhỏ.
5. Với dữ liệu AI đọc nhiều như rating, score, count, nên lưu sẵn trên bảng chính để tránh truy vấn nặng.

### 4. Nhóm bảng lý tưởng theo 1 schema thống nhất

Nếu muốn chuẩn hoá về một thiết kế “ideal” nhưng vẫn không phá code cũ, nên nhóm như sau:

- Nhóm cá nhân hoá: `users`, `user_profiles`, `user_goals`, `user_preference_profiles`, `user_feedback`
- Nhóm thực phẩm: `foods`, `ingredients`, `food_ingredients`, `food_details`, `food_recipes`
- Nhóm công thức và đánh giá: `food_recipes`, `recipe_ratings` nếu bạn thêm bảng rating riêng
- Nhóm dinh dưỡng và kế hoạch: `nutrition_logs`, `daily_nutrition_summary`, `meal_plans`, `meal_type_configs`
- Nhóm chat AI: `chat_sessions`, `chat_messages`, `chat_summaries`, `conversation_states`, `message_intents`, `intent_embeddings`, `chat_response_caches`
- Nhóm AI và quản trị: `ai_recommendations`, `search_events`, `audit_logs`, `system_metrics`, `food_verification_queue`

### 5. Gợi ý đặt tên để không xung đột

- Dùng tên bảng hiện tại nếu code đã phụ thuộc vào nó.
- Chỉ đặt tên mới cho phần thật sự chưa có trong dự án.
- Tránh tạo hai bảng có cùng ý nghĩa như `recipes` và `food_recipes` nếu không có lý do rõ ràng.
- Nếu cần bảng mới cho rating, dùng tên rõ nghĩa như `recipe_ratings` thay vì thêm rating trực tiếp vào `recipes` nếu bạn cần lịch sử đánh giá từng người dùng.

## Final Ideal Schema for Crawl + Pricing

Đây là phiên bản schema đầy đủ hơn để lưu được cả dữ liệu crawl giá nguyên liệu, món ăn sẵn, công thức, AI, và quản trị mà vẫn tránh xung đột với schema hiện tại. Khi đã dùng bộ này thì nên coi đây là nguồn chuẩn và chỉ mở rộng bằng migration, không tạo bảng trùng nghĩa.

### 1. Users & Profiles

### `users`
Mục đích sử dụng: Lưu tài khoản chính của người dùng, gồm đăng nhập, vai trò và trạng thái hoạt động.

### `user_profiles`
Mục đích sử dụng: Lưu thông tin cơ thể và hồ sơ sức khỏe để tính BMI, TDEE và mục tiêu calo.

### `user_behavior_profiles`
Mục đích sử dụng: Lưu sở thích ăn uống, món ghét, mô hình ăn uống và khẩu vị để cá nhân hóa gợi ý.

### `user_budgets`
Mục đích sử dụng: Lưu ngân sách chi tiêu của người dùng theo ngày, tuần hoặc bữa ăn.

### 2. Diseases & Goals

### `diseases`
Mục đích sử dụng: Lưu danh mục bệnh lý hoặc vấn đề sức khỏe để AI áp quy tắc dinh dưỡng phù hợp.

### `user_diseases`
Mục đích sử dụng: Gắn người dùng với các bệnh lý họ đang gặp để hệ thống lọc món an toàn.

### `disease_nutrition_rules`
Mục đích sử dụng: Lưu các ngưỡng dinh dưỡng theo bệnh, ví dụ giới hạn đường, muối, chất béo.

### `goals`
Mục đích sử dụng: Lưu danh mục mục tiêu thể hình hoặc mục tiêu sức khỏe như giảm cân, tăng cơ.

### `user_goals`
Mục đích sử dụng: Lưu mục tiêu hiện tại của từng người dùng và các giá trị đích liên quan.

### `goal_nutrition_rules`
Mục đích sử dụng: Lưu chỉ tiêu dinh dưỡng theo từng mục tiêu, ví dụ protein cho tăng cơ.

### 3. Ingredients Core & Pricing

### `ingredients`
Mục đích sử dụng: Lưu danh sách nguyên liệu chuẩn để dùng chung cho công thức, mua sắm và AI.

### `ingredient_aliases`
Mục đích sử dụng: Lưu tên đồng nghĩa của nguyên liệu để tìm kiếm và crawl dữ liệu không bị lệch tên.

### `ingredient_nutrition`
Mục đích sử dụng: Lưu thành phần dinh dưỡng chuẩn của nguyên liệu trên một đơn vị đo chuẩn.

### `ingredient_prices`
Mục đích sử dụng: Lưu giá hiện tại của nguyên liệu sau khi crawl từ WinMart, Bách Hóa Xanh hoặc nguồn khác.

### `ingredient_price_history`
Mục đích sử dụng: Lưu lịch sử biến động giá của nguyên liệu theo từng nguồn crawl để phân tích xu hướng giá.

### `unit_conversions`
Mục đích sử dụng: Lưu quy đổi giữa các đơn vị để AI tính đúng dinh dưỡng và chi phí theo gram, kg, cái, muỗng.

### `food_categories`
Mục đích sử dụng: Lưu nhóm phân loại món ăn hoặc thực phẩm để lọc và thống kê dễ hơn.

### `food_tags`
Mục đích sử dụng: Lưu tag bổ sung như chay, keto, cay, healthy để lọc món nhanh.

### 4. Foods Core

### `foods`
Mục đích sử dụng: Lưu các món ăn sẵn hoặc thực phẩm hoàn chỉnh mà AI có thể gợi ý, tính dinh dưỡng và gắn giá.

### `food_ingredients`
Mục đích sử dụng: Lưu quan hệ giữa món ăn và nguyên liệu cấu thành, kèm số lượng quy đổi.

### `food_tag_map`
Mục đích sử dụng: Gắn tag cho món ăn để phục vụ tìm kiếm, lọc và gợi ý thông minh.

### `food_recipes`
Mục đích sử dụng: Lưu hướng dẫn nấu hoặc chế biến cho từng món ăn.

### `food_embeddings`
Mục đích sử dụng: Lưu vector embedding của món ăn để AI tìm món tương đồng hoặc suy luận ngữ nghĩa.

### `food_prices`
Mục đích sử dụng: Lưu giá hiện tại của món ăn sẵn hoặc thực phẩm hoàn chỉnh sau khi crawl dữ liệu về.

### `food_price_history`
Mục đích sử dụng: Lưu lịch sử giá của từng món ăn sẵn theo thời gian và theo từng nguồn crawl.

### `crawl_sources`
Mục đích sử dụng: Lưu danh sách nguồn crawl như WinMart, Bách Hóa Xanh, cửa hàng tiện lợi hoặc nguồn API khác.

### `crawl_runs`
Mục đích sử dụng: Lưu mỗi lần crawl dữ liệu để biết đã crawl lúc nào, nguồn nào, trạng thái ra sao và có lỗi gì không.

### `crawl_items`
Mục đích sử dụng: Lưu từng bản ghi được crawl về trong một lần chạy, dùng để đối soát, khử trùng lặp và kiểm tra chất lượng dữ liệu.

### 5. Tracking, Budget & Feedback

### `user_budget_logs`
Mục đích sử dụng: Lưu lịch sử thay đổi ngân sách hoặc giới hạn chi tiêu của người dùng.

### `nutrition_logs`
Mục đích sử dụng: Lưu nhật ký ăn uống từng ngày của người dùng để tính dinh dưỡng thực tế.

### `daily_nutrition_summary`
Mục đích sử dụng: Lưu tổng hợp dinh dưỡng theo ngày để hiển thị dashboard nhanh và báo cáo.

### `user_feedback`
Mục đích sử dụng: Lưu đánh giá món ăn, like/dislike, lý do và phản hồi trực tiếp của người dùng.

### 6. AI & Recommendations

### `ai_recommendations`
Mục đích sử dụng: Lưu các món AI đã gợi ý cho người dùng cùng điểm phù hợp, chi phí ước tính và lý do gợi ý.

### `meal_recommendations`
Mục đích sử dụng: Lưu gợi ý món/bữa ăn đã được chấm điểm theo sức khỏe, ngân sách và mức độ khớp nhu cầu.

### `meal_plans`
Mục đích sử dụng: Lưu kế hoạch bữa ăn mà hệ thống hoặc người dùng tạo ra cho từng ngày.

### `chat_messages`
Mục đích sử dụng: Lưu nội dung tin nhắn chat giữa người dùng và AI để phân tích ý định và ngữ cảnh.

### `intent_patterns`
Mục đích sử dụng: Lưu câu mẫu và mẫu nhận diện intent để huấn luyện hoặc tinh chỉnh chatbot.

### `system_metrics`
Mục đích sử dụng: Lưu chỉ số hệ thống như hiệu năng crawl, số lượng dữ liệu, độ chính xác AI hoặc log vận hành.

### 7. Governance & Admin

### `food_verification_queue`
Mục đích sử dụng: Lưu các món hoặc nguyên liệu đang chờ kiểm duyệt sau khi crawl hoặc import.

### `audit_logs`
Mục đích sử dụng: Lưu lịch sử thay đổi dữ liệu để kiểm tra ai đã sửa gì, lúc nào và vì sao.

### `admin_settings`
Mục đích sử dụng: Lưu cấu hình hệ thống và thiết lập quản trị có thể thay đổi mà không cần sửa code.

### `crawl_sources`
Mục đích sử dụng: Lưu cấu hình nguồn crawl để hệ thống biết dữ liệu nào đến từ đâu.

### `crawl_runs`
Mục đích sử dụng: Lưu lịch sử các lượt crawl để theo dõi tiến trình và phát hiện lỗi crawler.

### `crawl_items`
Mục đích sử dụng: Lưu dữ liệu thô sau crawl trước khi được chuẩn hóa vào bảng chính.

### 8. Final Mapping Note

- Nếu bảng hiện tại đã có vai trò tương đương, hãy giữ nguyên tên đang dùng trong code để tránh vỡ migration.
- Nếu bảng mới chỉ thêm dữ liệu crawl hoặc pricing, hãy mở rộng bằng cột hoặc bảng con thay vì thay thế toàn bộ.
- Nếu cần đồng thời lưu nguyên liệu, thực phẩm sẵn và công thức, tách rõ 3 lớp: `ingredients` -> `foods` -> `food_recipes`.
- Nếu cần lịch sử giá, nên để `ingredient_prices` và có thể thêm `price_history` sau này, không ghi đè một giá duy nhất nếu bạn muốn phân tích xu hướng.
- Nếu cần lưu giá món ăn sẵn sau crawl, hãy để giá ở `food_prices` hoặc `food_price_history` thay vì trộn chung với `ingredient_prices`.
- Nếu cần lưu dữ liệu crawl thô, tách riêng `crawl_sources` -> `crawl_runs` -> `crawl_items` để không làm bẩn bảng chính.

## Ghi Chú

- Tài liệu này phản ánh trạng thái bảng hiện tại trong CSDL của dự án.
- Nếu chạy `migrate`, `repair_project_db`, hoặc thay đổi model, hãy cập nhật lại file này.
- Tài khoản custom chính nằm ở bảng `users`, không phải `auth_user`.

---

# Ideal Database Schema (Target Design)

Mục tiêu của schema này là dễ mở rộng, dễ truy vấn, giữ dữ liệu sạch và đủ linh hoạt cho các tính năng chính: người dùng, dinh dưỡng, công thức, đánh giá, chat AI, kế hoạch bữa ăn, thông tin giá crawl và quản trị.

**Lưu ý:** Dự án này là hệ thống gợi ý và thông tin, không phải nền tảng thương mại. Không có chức năng đặt hàng, thanh toán hay vận chuyển. Giá nguyên liệu/thực phẩm được crawl từ WinMart, Bách Hóa Xanh v.v. chỉ để cung cấp thông tin chi phí ước tính, không phải để bán hàng.

## Nguyên Tắc Thiết Kế Lý Tưởng

- Chuẩn hóa dữ liệu cốt lõi để tránh trùng lặp.
- Denormalize có chọn lọc cho các số liệu đọc nhiều như `avg_rating`, `total_ratings`.
- Mỗi bảng chỉ chịu trách nhiệm cho một thực thể rõ ràng.
- Dùng khóa ngoại và ràng buộc unique để giữ tính toàn vẹn.
- Tạo index theo luồng truy vấn thực tế, không tạo dàn trải.

## Các Ràng Buộc Quan Trọng

- Một người dùng chỉ có một đánh giá duy nhất cho một công thức.
- Một món ăn có đúng một công thức chính.
- `rating` chỉ nhận giá trị từ 1 đến 5.
- Dữ liệu xóa mềm dùng `is_deleted` thay vì xóa cứng nếu cần lịch sử.
- `avg_rating` và `total_ratings` cập nhật tự động từ bảng rating.

## Index Nên Có

- `nutrition_nutrition_log(account_id, date)`
- `nutrition_recipe(auto_added, avg_rating DESC)`
- `nutrition_recipe_rating(recipe_id, rating DESC)`
- `nutrition_recipe_rating(account_id)`
- `chat_chat_message(chat_session_id, created_at DESC)`
- `chat_chat_message(account_id, created_at DESC)`
- `core_models_ai_recommendation(account_id, created_at DESC)`
- `meal_plans_meal_plan(account_id, plan_date)`
- `users_user_goal(account_id, is_active)`
- `nutrition_ingredient_price(ingredient_id, source_name)`
- `nutrition_food_price(food_id, source_name)`
- `nutrition_crawl_run(source_id, created_at DESC)`

## Luồng Dữ Liệu Lý Tưởng

1. Người dùng tạo hồ sơ và mục tiêu dinh dưỡng.
2. Hệ thống lưu nhật ký ăn uống hằng ngày và tính tổng dinh dưỡng.
3. AI sinh công thức dựa trên thói quen ăn uống, nếu đủ tốt thì tự lưu vào `nutrition_recipe`.
4. Người dùng chấm sao công thức, `avg_rating` và `total_ratings` được cập nhật tự động.
5. AI dùng dữ liệu đánh giá + lịch sử ăn uống + mục tiêu để gợi ý món phù hợp.
6. Hệ thống crawl dữ liệu giá từ các nguồn thực phẩm (WinMart, Bách Hóa Xanh) để cung cấp thông tin chi phí ước tính.
7. Quản trị viên theo dõi audit log, metric hệ thống, và tình trạng các lần crawl.

## Kết Luận

Schema lý tưởng cho dự án này (hệ thống gợi ý thông tin, không bán hàng) nên bao gồm:

- 1 bảng tài khoản trung tâm
- 1 nhóm bảng hồ sơ, mục tiêu và ràng buộc sức khỏe của người dùng
- 1 nhóm bảng thực phẩm, nguyên liệu, công thức, đánh giá
- 1 nhóm bảng nhật ký dinh dưỡng và kế hoạch bữa ăn
- 1 nhóm bảng chat AI và cache phản hồi
- 1 nhóm bảng crawl dữ liệu giá (thông tin chỉ)
- 1 nhóm bảng gợi ý AI, audit log, và metric hệ thống

Thiết kế này đủ đơn giản để bảo trì, đủ chuẩn hóa để sạch dữ liệu, không có phức tạp từ thương mại, và đủ mở rộng khi hệ thống tăng trưởng về số lượng người dùng, công thức và tính năng AI.
