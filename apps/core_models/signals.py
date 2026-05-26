"""
Django signals to prevent ID gaps when records are deleted.
This auto-maintains sequential IDs starting from 1 with no gaps.
"""

from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db import connection
from apps.nutrition.models import (
    FoodCategory, Food, FoodIngredient, Recipe, FoodPopularity
)
from apps.meal_plans.models import MealPlan
from apps.chat.models import ChatSession, ChatMessage, Intent


def close_gaps_in_table(table_name):
    """
    Close ID gaps in a table after deletion.
    Renumbers remaining IDs to be sequential from 1 to count.
    """
    cursor = connection.cursor()
    vendor = connection.vendor
    
    # Get current row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    
    if count == 0:
        return
    
    # Get all current IDs in order
    cursor.execute(f"SELECT id FROM {table_name} ORDER BY id")
    ids = [row[0] for row in cursor.fetchall()]
    
    # Check if sequential
    expected = list(range(1, count + 1))
    if ids == expected:
        return  # Already sequential
    
    # Disable FK constraints temporarily
    if vendor == 'postgresql':
        cursor.execute("SET session_replication_role = 'replica'")
    
    try:
        # Build mapping and renumber
        id_mapping = {old_id: new_id for new_id, old_id in enumerate(ids, start=1)}
        
        # Move to temp IDs first
        for new_id, (old_id, new_id_final) in enumerate(id_mapping.items(), start=1):
            temp_id = -1000000 - new_id
            cursor.execute(f"UPDATE {table_name} SET id = %s WHERE id = %s", [temp_id, old_id])
        
        # Then to final IDs
        for new_id, old_id in enumerate(ids, start=1):
            temp_id = -1000000 - new_id
            cursor.execute(f"UPDATE {table_name} SET id = %s WHERE id = %s", [new_id, temp_id])
        
        # Reset sequence
        if vendor == 'postgresql':
            cursor.execute(f"ALTER SEQUENCE {table_name}_id_seq RESTART WITH {count + 1}")
    finally:
        if vendor == 'postgresql':
            cursor.execute("SET session_replication_role = 'origin'")


# Register signals for all relevant models
@receiver(post_delete, sender=FoodCategory)
def close_food_category_gaps(sender, **kwargs):
    close_gaps_in_table('food_categories')


@receiver(post_delete, sender=Food)
def close_food_gaps(sender, **kwargs):
    close_gaps_in_table('foods')


@receiver(post_delete, sender=FoodIngredient)
def close_food_ingredient_gaps(sender, **kwargs):
    close_gaps_in_table('food_ingredients')


@receiver(post_delete, sender=Recipe)
def close_food_recipe_gaps(sender, **kwargs):
    close_gaps_in_table('food_recipes')


@receiver(post_delete, sender=MealPlan)
def close_meal_plan_gaps(sender, **kwargs):
    close_gaps_in_table('meal_plans')


@receiver(post_delete, sender=ChatSession)
def close_chat_session_gaps(sender, **kwargs):
    close_gaps_in_table('chat_sessions')


@receiver(post_delete, sender=ChatMessage)
def close_chat_message_gaps(sender, **kwargs):
    close_gaps_in_table('chat_messages')


@receiver(post_delete, sender=Intent)
def close_intent_gaps(sender, **kwargs):
    close_gaps_in_table('intents')
