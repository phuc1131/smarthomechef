"""
Centralized API/Service Hub
========================

Một nơi duy nhất để import tất cả external APIs và services.
Giúp code dễ maintain hơn và tránh circular imports.

Usage:
    from apps.core_models.api_hub import AI_AVAILABLE, call_gemini_with_debug
    from apps.core_models.api_hub import MealPlanGeneratorService
    from apps.core_models.api_hub import health_score_from_meal_feedback
"""

# ===== EXTERNAL APIs & AI =====
from app.services.external_apis import (
    AI_AVAILABLE,
    GEMINI_API_KEY,
    SPOONACULAR_API_KEY,
    call_gemini_with_debug,
    _gemini_generate_text,
    fetch_spoonacular_food,
    get_spoonacular_last_error,
    parse_and_save_spoonacular_food,
)

# ===== AI ORCHESTRATION =====
from app.services.ai_orchestrator_service import (
    AIOrchestratorService,
)

# ===== TRAINING / PERSONALIZATION =====
from app.services.model_training_service import (
    get_intent_model_status,
    predict_intent,
    predict_top_intents,
    train_intent_classifier,
)
from app.services.personalization_service import (
    build_user_preference_profile,
    get_personalization_context,
    rank_food_candidates,
    score_food_for_user,
    summarize_ai_activity,
)

# ===== MEAL PLAN GENERATION =====
from app.services.meal_plan_generator_service import (
    MealPlanGeneratorService,
)

# ===== FOOD DATA SERVICES =====
from app.services.food_data_service import (
    get_or_fetch_food,
    ensure_ingredient_nutrition,
)

# ===== HEALTH & FEEDBACK =====
from app.services.health_feedback_service import (
    health_score_from_meal_feedback,
    update_user_feedback_and_preferences,
)

# ===== CHAT & TEXT =====
from app.services.chat_text_service import (
    tokenize_chat_text,
    extract_intent_keywords,
    categorize_chat_message,
)

# ===== INGREDIENT PARSING =====
from app.services.ingredient_parser_service import (
    parse_ingredients_from_text,
)

# ===== RECIPE GENERATION =====
from app.services.recipe_generator_service import (
    recommend_recipes_from_ingredients,
    generate_recipe_details,
)

# ===== RECIPE VARIATIONS =====
from app.services.recipe_variations_service import (
    generate_recipe_variations,
)

# ===== GROCERY LIST =====
from app.services.grocery_list_service import (
    generate_shopping_list_from_meal_plan,
    calculate_shopping_cost_estimate,
)

__all__ = [
    # AI & External
    'AI_AVAILABLE',
    'GEMINI_API_KEY',
    'SPOONACULAR_API_KEY',
    'call_gemini_with_debug',
    '_gemini_generate_text',
    'fetch_spoonacular_food',
    'get_spoonacular_last_error',
    'parse_and_save_spoonacular_food',

    # AI Orchestration
    'AIOrchestratorService',

    # Training / Personalization
    'get_intent_model_status',
    'predict_intent',
    'predict_top_intents',
    'train_intent_classifier',
    'build_user_preference_profile',
    'get_personalization_context',
    'rank_food_candidates',
    'score_food_for_user',
    'summarize_ai_activity',
    
    # Meal Planning
    'MealPlanGeneratorService',
    
    # Food Data
    'get_or_fetch_food',
    'ensure_ingredient_nutrition',
    
    # Health
    'health_score_from_meal_feedback',
    'update_user_feedback_and_preferences',
    
    # Chat
    'tokenize_chat_text',
    'extract_intent_keywords',
    'categorize_chat_message',
    
    # Ingredients
    'parse_ingredients_from_text',
    
    # Recipes
    'recommend_recipes_from_ingredients',
    'generate_recipe_details',
    'generate_recipe_variations',
    
    # Shopping
    'generate_shopping_list_from_meal_plan',
    'calculate_shopping_cost_estimate',
]
