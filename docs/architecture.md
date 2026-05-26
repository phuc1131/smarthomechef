# Project Structure - Enterprise Clean Architecture

## Overview
This project has been restructured into a modern, feature-based Django application with clear separation of concerns. The new structure follows enterprise best practices for maintainability, scalability, and collaboration.

## Folder Structure

```
noi-tro-ai/
├── noi_tro_ai/               # Django project settings
│   ├── settings.py          # Main Django configuration
│   ├── urls.py              # Root URL routing
│   └── wsgi.py              # WSGI application
│
├── apps/                    # Feature-based Django applications
│   ├── users/              # User management (accounts, profiles, goals, feedback)
│   │   ├── models.py       # Account, UserProfile, UserGoal, UserFeedback, UserPreferenceProfile
│   │   ├── admin.py        # Django admin config
│   │   ├── urls.py         # App URL routing
│   │   └── apps.py         # App config
│   │
│   ├── chat/               # Chat & NLP (messaging, intents, embeddings)
│   │   ├── models.py       # ChatSession, ChatMessage, Intent, Pattern, IntentEmbedding, etc.
│   │   ├── admin.py        # Django admin config
│   │   ├── urls.py         # App URL routing
│   │   └── apps.py         # App config
│   │
│   ├── nutrition/          # Nutrition & food tracking
│   │   ├── models.py       # Food, NutritionLog, Recipe, Ingredients, Translations
│   │   ├── admin.py        # Django admin config
│   │   ├── urls.py         # App URL routing
│   │   └── apps.py         # App config
│   │
│   ├── meal_plans/         # Meal planning
│   │   ├── models.py       # MealPlan, MealTypeConfig
│   │   ├── admin.py        # Django admin config
│   │   ├── urls.py         # App URL routing
│   │   └── apps.py         # App config
│   │
│   ├── admin_panel/        # Admin dashboard & management
│   │   ├── apps.py         # App config
│   │   ├── urls.py         # Admin URL routing
│   │   └── views.py        # Admin views
│   │
│   └── core_models/        # Cross-feature models
│       ├── models.py       # AIRecommendation, SearchEvent
│       ├── admin.py        # Django admin config
│       └── apps.py         # App config
│
├── app/                    # Legacy app (being phased out)
│   ├── models.py           # EMPTY - all models moved to feature apps
│   ├── admin.py            # EMPTY - all admin moved to feature apps
│   ├── views.py            # Views importing from feature-based apps
│   ├── db_connector.py     # Centralized model import point
│   ├── services/           # Shared business logic
│   │   ├── external_apis.py
│   │   ├── chat_text_service.py
│   │   ├── health_feedback_service.py
│   │   ├── food_data_service.py
│   │   ├── personalization_service.py
│   │   └── model_training_service.py
│   ├── features/           # Feature-specific functionality
│   │   ├── admin_panel/
│   │   │   ├── data_manager_service.py
│   │   │   └── views.py
│   │   └── user_panel/
│   │       └── views.py
│   ├── templates/          # HTML templates
│   ├── static/             # CSS, JS, images
│   └── management/
│       └── commands/       # Django management commands
│
├── services/               # Global service compatibility wrappers
├── tests/                  # Unit & integration tests
├── tools/                  # Operational tooling by function
│   ├── database/           # DB setup, migration, verification scripts
│   ├── diagnostics/        # System and runtime diagnostics
│   ├── maintenance/        # Data maintenance/backfill scripts
│   ├── seeding/            # Seed and bootstrap data scripts
│   └── validation/         # Validation and QA scripts
├── database/               # Database assets (SQL schema, migrations assets)
│
├── manage.py              # Django management
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
└── db.sqlite3            # SQLite database (development)
```

## Model Organization by Feature

### 1. **apps/users/** - User Management
- `Account`: Main user account model
- `UserProfile`: Extended user profile with health info
- `UserGoal`: User health goals
- `UserFeedback`: User feedback on foods/recommendations
- `UserPreferenceProfile`: Aggregated user preferences

**Admin interface:** Full CRUD for user management
**Key features:** Account creation, profile management, goal tracking

### 2. **apps/chat/** - Chat & NLP
- `ChatSession`: Conversation sessions
- `ChatMessage`: Individual messages
- `Intent`: Conversation intention/topic classification
- `Pattern`: Training patterns for intent recognition
- `MessageIntent`: Message-to-intent mapping with confidence
- `IntentEmbedding`: Vector embeddings for semantic matching
- `ChatSummary`: Auto-generated session summaries
- `ConversationState`: Multi-turn conversation tracking
- `ChatResponseCache`: Cached AI responses to reduce API calls

**Admin interface:** Monitor conversations, manage intents, debug embeddings
**Key features:** Intent classification, embedding-based similarity, response caching

### 3. **apps/nutrition/** - Food & Nutrition
- `Food`: Food database with nutritional info
- `FoodDetail`: Extended nutritional details (vitamins, minerals)
- `Ingredient`: Raw ingredients for food composition
- `FoodIngredient`: Many-to-many relationship for food composition
- `NutritionLog`: Actual daily nutrition tracking
- `DailyNutritionSummary`: Daily nutrition aggregation
- `Recipe`: Cooking recipes with instructions & ingredients
- `RecipeTranslation`: Cached recipe translations
- `TextTranslation`: Cached text translations

**Admin interface:** Food database management, nutrition tracking, recipe browsing
**Key features:** Food search, nutrition calculation, recipe management, translation caching

### 4. **apps/meal_plans/** - Meal Planning
- `MealPlan`: User meal plans by date/meal type
- `MealTypeConfig`: Configuration for meal types (breakfast, lunch, etc.)

**Admin interface:** Meal plan management & configuration
**Key features:** Weekly meal planning, meal type customization

### 5. **apps/core_models/** - Cross-Feature Models
- `AIRecommendation`: AI-generated food recommendations
- `SearchEvent`: Track user search behavior for analytics

**Admin interface:** View recommendations & search analytics
**Key features:** AI recommendations, user analytics

## Class Descriptions for Class Diagram

Chỉ giữ các lớp chính thực sự quan trọng, trình bày theo kiểu UML ngắn gọn.

### 1. Account

**Thuộc tính chính**
- `id`
- `username`
- `email`
- `password_hash`
- `role`
- `is_active`
- `created_at`

**Phương thức chính**
- `__str__()`

**Quan hệ**
- 1-1 với `UserProfile`
- 1-n với `MealPlan`, `NutritionLog`, `ChatSession`, `UserFeedback`, `UserBehaviorLog`, `MealRecommendation`

### 2. UserProfile

**Thuộc tính chính**
- `id`
- `account`
- `name`
- `age`
- `gender`
- `height`
- `weight`
- `activity_level`
- `health_goal`
- `medical_conditions`
- `dietary_preferences`
- `bmi`
- `daily_calorie_target`
- `budget_limit`
- `created_at`
- `updated_at`

**Phương thức chính**
- `__str__()`

**Quan hệ**
- Thuộc về `Account`

### 3. Food

**Thuộc tính chính**
- `id`
- `name`
- `normalized_name`
- `category`
- `calories`
- `protein`
- `carbs`
- `fat`
- `fiber`
- `description`
- `image_url`
- `tags`
- `created_at`

**Phương thức chính**
- `__str__()`
- `total_calories`
- `total_protein`
- `total_carbs`
- `total_fat`
- `category_name`

**Quan hệ**
- N-1 với `FoodCategory`
- 1-n với `Ingredient`, `Recipe`, `NutritionLog`, `MealPlan`

### 4. Ingredient

**Thuộc tính chính**
- `name`
- `normalized_name`
- `is_deleted`

**Phương thức chính**
- `__str__()`
- `save()`

**Quan hệ**
- 1-n với `IngredientAlias`, `IngredientNutrition`, `IngredientPrice`, `UnitConversion`
- N-n với `Food` thông qua `FoodIngredient`

### 5. NutritionLog

**Thuộc tính chính**
- `id`
- `account`
- `food`
- `date`
- `meal_type`
- `servings`
- `total_calories`
- `total_protein`
- `total_carbs`
- `total_fat`
- `created_at`

**Phương thức chính**
- `__str__()`
- `computed_total_calories`
- `computed_total_protein`
- `computed_total_carbs`
- `computed_total_fat`

**Quan hệ**
- Thuộc về `Account`
- Thuộc về `Food`

### 6. MealPlan

**Thuộc tính chính**
- `id`
- `account`
- `food`
- `stt`
- `date`
- `meal_type`
- `servings`
- `notes`
- `created_at`

**Phương thức chính**
- `__str__()`

**Quan hệ**
- Thuộc về `Account`
- Thuộc về `Food`

### 7. ChatSession

**Thuộc tính chính**
- `id`
- `account`
- `title`
- `created_at`
- `missing_fields`
- `ask_count`
- `current_intent_id`
- `filled_fields`
- `updated_at`

**Phương thức chính**
- `__str__()`

**Quan hệ**
- Thuộc về `Account`
- 1-n với `ChatMessage`, `ChatSummary`

### 8. ChatMessage

**Thuộc tính chính**
- `id`
- `session`
- `role`
- `content`
- `created_at`

**Phương thức chính**
- `__str__()`

**Quan hệ**
- Thuộc về `ChatSession`
- 1-n với `MessageIntent`, `IntentEmbedding`

### 9. Intent

**Thuộc tính chính**
- `id`
- `name`
- `description`
- `required_fields`
- `topic`

**Phương thức chính**
- `__str__()`

**Quan hệ**
- 1-n với `Pattern`
- 1-n với `MessageIntent`

### 10. Pattern

**Thuộc tính chính**
- `id`
- `intent`
- `text`

**Phương thức chính**
- `__str__()`

**Quan hệ**
- Thuộc về `Intent`

### 11. MealRecommendation

**Thuộc tính chính**
- `account`
- `food`
- `score`
- `match_score`
- `budget_score`
- `health_score`
- `reason`
- `ai_model_version`
- `created_at`

**Phương thức chính**
- `__str__()`

**Quan hệ**
- Thuộc về `Account`
- Thuộc về `Food`

### 12. Gợi ý vẽ biểu đồ lớp

- Chỉ giữ các lớp chính: `Account`, `UserProfile`, `Food`, `Ingredient`, `NutritionLog`, `MealPlan`, `ChatSession`, `ChatMessage`, `Intent`, `Pattern`, `MealRecommendation`.
- Nếu biểu đồ quá nhiều chi tiết, có thể bỏ các lớp phụ trợ như `FoodTag`, `IngredientAlias`, `IngredientPrice`, `DailyNutritionSummary`, `ChatResponseCache`, `ModelMetadata`.
- Các quan hệ quan trọng nhất: `Account`-`UserProfile`, `Account`-`MealPlan`, `Account`-`NutritionLog`, `Food`-`Ingredient`, `ChatSession`-`ChatMessage`, `Intent`-`Pattern`.

## Import Guidelines

### ✅ CORRECT Way to Import Models

```python
# From feature apps (NEW)
from apps.users.models import Account, UserProfile
from apps.chat.models import ChatSession, ChatMessage, Intent
from apps.nutrition.models import Food, NutritionLog, Recipe
from apps.meal_plans.models import MealPlan
from apps.core_models.models import AIRecommendation, SearchEvent

# From centralized connector (ALTERNATIVE)
from app.db_connector import Account, ChatSession, Food, MealPlan
```

### ❌ INCORRECT Way (DEPRECATED)

```python
# DON'T use these anymore:
from app.models import Account         # WRONG - app/models.py is now empty
from .models import ChatSession       # WRONG - old structure
```

## Migration Status

✅ **Completed:**
- Created 6 feature-based Django apps
- Migrated all 35+ models to feature apps
- Updated imports in all Python files
- Created admin.py for each app
- Generated new migrations (0012_*)

⏳ **Pending:**
- Run `python manage.py migrate` to apply database changes
- Remove deprecated `app` app from INSTALLED_APPS (after full migration)
- Organize shared services into `services/` directory
- Consolidate utilities into `utils/` directory

## Restructuring Snapshot

This snapshot consolidates previous restructuring notes so there is a single architecture reference.

### Completed Work
- Created 6 feature-based Django apps under `apps/`.
- Migrated 35+ models into feature apps (`users`, `chat`, `nutrition`, `meal_plans`, `core_models`).
- Updated imports in views, services, and maintenance scripts to use `apps.*.models`.
- Added admin registrations per feature app.
- Added architecture, style, and database schema documentation.

### Operational Notes
- Legacy `app/` is still present for compatibility and forwards logic to feature modules.
- `app/models.py` and `app/admin.py` are intentionally kept minimal while migration is phased.
- Current root docs for structure/restructuring have been consolidated into this file.

## Running the Application

### Initial Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Access Points
- **User Interface**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin/
- **Chat API**: http://localhost:8000/chat/
- **Nutrition API**: http://localhost:8000/nutrition/

## Key Architecture Principles

### 1. **Feature-Based Organization**
Each feature (users, chat, nutrition) is a self-contained Django app with its own models, views, URLs, and admin configurations.

### 2. **Single Responsibility**
Each app has one primary responsibility:
- `users/` → User authentication & profile management
- `chat/` → Conversational AI & intent recognition
- `nutrition/` → Food database & nutrition tracking
- `meal_plans/` → Meal planning
- `core_models/` → Cross-cutting concerns

### 3. **Clear Dependencies**
- Apps import from other apps only when necessary
- Central `app/db_connector.py` provides unified import point
- Circular imports avoided through lazy imports in services

### 4. **Scalability**
- Easy to add new features (create new app folder)
- Easy to understand feature scope (look in `apps/feature_name/`)
- Easy to locate bugs (feature → app folder)

## Future Improvements

1. **Move remaining code to feature apps:**
   - Move views from `app/views.py` to respective feature apps
   - Move services from `app/services/` to feature-based service modules
   
2. **Organize utilities:**
   - Create `utils/` for shared helper functions
   - Create `services/` for cross-feature business logic

3. **Improve testing:**
   - Add unit tests in each app's `tests/` folder
   - Add integration tests for workflows

4. **Documentation:**
   - Add API documentation (Django REST Swagger)
   - Add ER diagram for database schema

## Common Tasks

### Add a New Feature
```bash
# 1. Create app structure
python manage.py startapp apps/newfeature

# 2. Define models in apps/newfeature/models.py
# 3. Create admin in apps/newfeature/admin.py
# 4. Add URLs in apps/newfeature/urls.py
# 5. Register in noi_tro_ai/settings.py INSTALLED_APPS
# 6. Create migrations
python manage.py makemigrations
python manage.py migrate
```

### Access Django Admin
1. Create superuser: `python manage.py createsuperuser`
2. Navigate to: `http://localhost:8000/admin/`
3. Use each app's admin interface to manage models

### Run Tests
```bash
python manage.py test
```

## Support & Questions

For questions about the new structure, refer to:
1. **Model location**: Check [Folder Structure section](#folder-structure)
2. **Import issues**: Check [Import Guidelines section](#import-guidelines)
3. **Adding features**: Check [Common Tasks section](#common-tasks)
