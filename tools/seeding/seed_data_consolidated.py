#!/usr/bin/env python
"""
Consolidated seed data script for Smart Chef project.
This is the single source of truth for all seed operations.

Usage:
    python tools/seeding/seed_data_consolidated.py                    # Seed everything
    python tools/seeding/seed_data_consolidated.py --foods            # Seed only foods
    python tools/seeding/seed_data_consolidated.py --intents          # Seed only intents
    python tools/seeding/seed_data_consolidated.py --patterns         # Seed only intent patterns
"""

import os
import sys
import django
import argparse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from apps.users.models import Account, UserProfile
from apps.nutrition.models import Food, FoodCategory
from apps.chat.models import Intent, Pattern, ChatSession, ChatMessage, MessageIntent

# ============================================================================
# 1. FOOD DATA
# ============================================================================

FOODS_DATA = [
    {"name": "Pho bo", "category": "Mon nuoc", "calories": 350, "protein": 20, "carbs": 40, "fat": 10, "fiber": 1, "serving_size": "1 to (400ml)", "description": "Mon pho truyen thong Viet Nam voi nuoc dung bo va banh pho", "is_vegetarian": False, "is_diabetes_friendly": False, "is_weight_loss_friendly": False},
    {"name": "Bun cha", "category": "Mon nuoc", "calories": 450, "protein": 25, "carbs": 45, "fat": 18, "fiber": 2, "serving_size": "1 phan", "description": "Bun cha Ha Noi voi thit nuong va nuoc cham", "is_vegetarian": False, "is_diabetes_friendly": False, "is_weight_loss_friendly": False},
    {"name": "Com rang trung", "category": "Mon com", "calories": 400, "protein": 12, "carbs": 55, "fat": 15, "fiber": 1, "serving_size": "1 dia", "description": "Com chien voi trung va rau cu", "is_vegetarian": True, "is_diabetes_friendly": False, "is_weight_loss_friendly": False},
    {"name": "Goi cuon", "category": "Mon cuon", "calories": 120, "protein": 8, "carbs": 15, "fat": 3, "fiber": 2, "serving_size": "2 cuon", "description": "Goi cuon tom thit voi rau song va banh trang", "is_vegetarian": False, "is_diabetes_friendly": True, "is_weight_loss_friendly": True},
    {"name": "Canh chua ca", "category": "Mon canh", "calories": 180, "protein": 15, "carbs": 12, "fat": 8, "fiber": 3, "serving_size": "1 bat (300ml)", "description": "Canh chua mien Nam voi ca va rau", "is_vegetarian": False, "is_diabetes_friendly": True, "is_weight_loss_friendly": True},
    {"name": "Banh mi thit", "category": "Mon banh", "calories": 380, "protein": 18, "carbs": 42, "fat": 14, "fiber": 2, "serving_size": "1 o", "description": "Banh mi Viet Nam voi nhan thit va rau", "is_vegetarian": False, "is_diabetes_friendly": False, "is_weight_loss_friendly": False},
    {"name": "Bun bo Hue", "category": "Mon nuoc", "calories": 420, "protein": 22, "carbs": 48, "fat": 14, "fiber": 2, "serving_size": "1 to", "description": "Bun bo dac san Hue voi nuoc dung dam da", "is_vegetarian": False, "is_diabetes_friendly": False, "is_weight_loss_friendly": False},
    {"name": "Rau muong xao toi", "category": "Mon rau", "calories": 85, "protein": 3, "carbs": 8, "fat": 5, "fiber": 4, "serving_size": "1 dia", "description": "Rau muong xao voi toi, mon rau don gian va bo duong", "is_vegetarian": True, "is_diabetes_friendly": True, "is_weight_loss_friendly": True},
    {"name": "Ca kho to", "category": "Mon kho", "calories": 250, "protein": 20, "carbs": 8, "fat": 15, "fiber": 0, "serving_size": "1 phan", "description": "Ca kho to kieu mien Nam voi nuoc mau thom", "is_vegetarian": False, "is_diabetes_friendly": False, "is_weight_loss_friendly": False},
    {"name": "Trung chien", "category": "Mon trung", "calories": 150, "protein": 10, "carbs": 1, "fat": 12, "fiber": 0, "serving_size": "2 qua", "description": "Trung ga chien vang", "is_vegetarian": True, "is_diabetes_friendly": True, "is_weight_loss_friendly": False},
    {"name": "Thit kho trung", "category": "Mon kho", "calories": 320, "protein": 22, "carbs": 10, "fat": 22, "fiber": 0, "serving_size": "1 phan", "description": "Thit ba roi kho voi trung va nuoc dua", "is_vegetarian": False, "is_diabetes_friendly": False, "is_weight_loss_friendly": False},
    {"name": "Salad rau cu", "category": "Mon rau", "calories": 95, "protein": 3, "carbs": 12, "fat": 4, "fiber": 5, "serving_size": "1 dia", "description": "Salad rau tuoi voi dau giam", "is_vegetarian": True, "is_diabetes_friendly": True, "is_weight_loss_friendly": True},
    {"name": "Chao ga", "category": "Mon chao", "calories": 200, "protein": 12, "carbs": 30, "fat": 4, "fiber": 1, "serving_size": "1 to", "description": "Chao ga nong hoi, tot cho suc khoe", "is_vegetarian": False, "is_diabetes_friendly": True, "is_weight_loss_friendly": True},
    {"name": "Mi xao bo", "category": "Mon mi", "calories": 450, "protein": 20, "carbs": 50, "fat": 18, "fiber": 2, "serving_size": "1 dia", "description": "Mi xao voi thit bo va rau cu", "is_vegetarian": False, "is_diabetes_friendly": False, "is_weight_loss_friendly": False},
    {"name": "Dau hu sot ca chua", "category": "Mon chay", "calories": 160, "protein": 10, "carbs": 12, "fat": 8, "fiber": 2, "serving_size": "1 dia", "description": "Dau hu chien gion sot ca chua", "is_vegetarian": True, "is_diabetes_friendly": True, "is_weight_loss_friendly": True},
    {"name": "Ga nuong mat ong", "category": "Mon nuong", "calories": 350, "protein": 30, "carbs": 15, "fat": 18, "fiber": 0, "serving_size": "1 phan", "description": "Ga nuong thom voi mat ong va gia vi", "is_vegetarian": False, "is_diabetes_friendly": False, "is_weight_loss_friendly": False},
    {"name": "Com trang", "category": "Mon com", "calories": 200, "protein": 4, "carbs": 44, "fat": 0.5, "fiber": 0.5, "serving_size": "1 chen", "description": "Com trang nau chin", "is_vegetarian": True, "is_diabetes_friendly": False, "is_weight_loss_friendly": False},
    {"name": "Sup bi do", "category": "Mon canh", "calories": 120, "protein": 3, "carbs": 20, "fat": 3, "fiber": 4, "serving_size": "1 bat (300ml)", "description": "Sup bi do mem min, giau vitamin A", "is_vegetarian": True, "is_diabetes_friendly": True, "is_weight_loss_friendly": True},
    {"name": "Trung hap", "category": "Mon trung", "calories": 130, "protein": 11, "carbs": 1, "fat": 9, "fiber": 0, "serving_size": "1 phan", "description": "Trung hap mem, de an va bo duong", "is_vegetarian": True, "is_diabetes_friendly": True, "is_weight_loss_friendly": True},
    {"name": "Nom bo kho", "category": "Mon goi", "calories": 180, "protein": 15, "carbs": 10, "fat": 9, "fiber": 3, "serving_size": "1 dia", "description": "Nom bo kho gion voi rau va dau phong", "is_vegetarian": False, "is_diabetes_friendly": True, "is_weight_loss_friendly": True},
]

# ============================================================================
# 2. INTENTS DATA
# ============================================================================

INTENTS_DATA = [
    {
        'name': 'recommendation',
        'topic': 'Food Recommendation',
        'description': 'Gợi ý và đề xuất các món ăn'
    },
    {
        'name': 'nutrition',
        'topic': 'Nutrition Advice',
        'description': 'Tư vấn về dinh dưỡng, vitamins, minerals'
    },
    {
        'name': 'meal_plan',
        'topic': 'Meal Planning',
        'description': 'Lên kế hoạch thực đơn hàng ngày, hàng tuần'
    },
    {
        'name': 'general',
        'topic': 'General Chat',
        'description': 'Hội thoại chung'
    },
    {
        'name': 'health_goal',
        'topic': 'Health Goals',
        'description': 'Hỗ trợ đạt mục tiêu sức khỏe'
    },
    {
        'name': 'feedback',
        'topic': 'User Feedback',
        'description': 'Phàn nàn/góp ý/đánh giá từ người dùng'
    },
    {
        'name': 'ingredient',
        'topic': 'Ingredient Query',
        'description': 'Hỏi về nguyên liệu, nguyên liệu sẵn có, thay thế nguyên liệu'
    },
    {
        'name': 'budget',
        'topic': 'Budget Planning',
        'description': 'Lập món hoặc thực đơn theo ngân sách'
    },
    {
        'name': 'recipe',
        'topic': 'Recipe Cooking',
        'description': 'Tìm công thức, cách nấu, cách chế biến'
    },
    {
        'name': 'shopping',
        'topic': 'Shopping List',
        'description': 'Danh sách mua sắm nguyên liệu, đồ ăn'
    },
]

# ============================================================================
# 3. INTENT PATTERNS DATA
# ============================================================================

INTENT_PATTERNS_DATA = [
    # Recommendation intent - "Suggest me something to eat"
    {'intent': 'recommendation', 'pattern': 'gợi ý cho tôi', 'confidence': 0.95, 'verified_by_admin': True},
    {'intent': 'recommendation', 'pattern': 'hôm nay ăn gì', 'confidence': 0.95, 'verified_by_admin': True},
    {'intent': 'recommendation', 'pattern': 'có đồ gì ngon không', 'confidence': 0.90, 'verified_by_admin': True},
    {'intent': 'recommendation', 'pattern': 'tôi muốn ăn cái gì', 'confidence': 0.85, 'verified_by_admin': True},
    {'intent': 'recommendation', 'pattern': 'đề xuất thực đơn', 'confidence': 0.90, 'verified_by_admin': True},
    
    # Health intent
    {'intent': 'health_goal', 'pattern': 'tôi muốn giảm cân', 'confidence': 0.98, 'verified_by_admin': True},
    {'intent': 'health_goal', 'pattern': 'tôi bị tiểu đường', 'confidence': 0.98, 'verified_by_admin': True},
    {'intent': 'health_goal', 'pattern': 'tôi muốn tăng cơ', 'confidence': 0.95, 'verified_by_admin': True},
    {'intent': 'health_goal', 'pattern': 'tôi có bệnh', 'confidence': 0.90, 'verified_by_admin': True},
    {'intent': 'health_goal', 'pattern': 'mục tiêu sức khỏe', 'confidence': 0.85, 'verified_by_admin': True},
    
    # Ingredient intent
    {'intent': 'ingredient', 'pattern': 'tôi có trứng', 'confidence': 0.95, 'verified_by_admin': True},
    {'intent': 'ingredient', 'pattern': 'nguyên liệu là', 'confidence': 0.92, 'verified_by_admin': True},
    {'intent': 'ingredient', 'pattern': 'tôi chỉ có', 'confidence': 0.90, 'verified_by_admin': True},
    {'intent': 'ingredient', 'pattern': 'tôi có những thứ', 'confidence': 0.88, 'verified_by_admin': True},
    {'intent': 'ingredient', 'pattern': 'làm gì với', 'confidence': 0.85, 'verified_by_admin': True},
    
    # Budget intent
    {'intent': 'budget', 'pattern': 'tôi có 50 ngàn', 'confidence': 0.95, 'verified_by_admin': True},
    {'intent': 'budget', 'pattern': 'ngân sách là', 'confidence': 0.92, 'verified_by_admin': True},
    {'intent': 'budget', 'pattern': 'mua sắm với 100k', 'confidence': 0.90, 'verified_by_admin': True},
    {'intent': 'budget', 'pattern': 'tôi muốn tiết kiệm', 'confidence': 0.85, 'verified_by_admin': True},
    {'intent': 'budget', 'pattern': 'chi phí tối đa', 'confidence': 0.88, 'verified_by_admin': True},
    
    # Nutrition intent
    {'intent': 'nutrition', 'pattern': 'dinh dưỡng của', 'confidence': 0.95, 'verified_by_admin': True},
    {'intent': 'nutrition', 'pattern': 'bao nhiêu calo', 'confidence': 0.95, 'verified_by_admin': True},
    {'intent': 'nutrition', 'pattern': 'có bao nhiêu protein', 'confidence': 0.93, 'verified_by_admin': True},
    {'intent': 'nutrition', 'pattern': 'carbs trong', 'confidence': 0.90, 'verified_by_admin': True},
]

MESSAGE_INTENT_SAMPLES = [
    ('recommendation', 'Goi y bua an phu hop cho toi', 'Minh uu tien mon an lanh manh va de nau.'),
    ('recommendation', 'Hom nay an gi de nhieu protein hon', 'Minh se uu tien mon giau protein va it dau mo.'),
    ('meal_plan', 'Lap thuc don 7 ngay cho toi', 'Minh se lap thuc don can bang cho tung ngay.'),
    ('meal_plan', 'Toi muon thuc don theo ngan sach 100k', 'Minh se loc mon re va dung ngan sach.'),
    ('nutrition', 'Mon nay co bao nhieu calo', 'Minh se tra thong tin dinh duong cua mon nay.'),
    ('nutrition', 'Toi can biet protein va carbs', 'Minh se tong hop macros cho ban.'),
    ('health_goal', 'Toi muon giam can nhanh', 'Minh se uu tien mon it calo va dieu tiet khau phan.'),
    ('health_goal', 'Toi bi tieu duong thi nen an gi', 'Minh se loc mon than thien voi duong huyet.'),
    ('feedback', 'Mon nay khong hop vi toi', 'Minh se ghi nhan feedback cua ban.'),
    ('general', 'Chao ban', 'Minh co the giup gi hom nay?'),
    ('ingredient', 'Toi chi co trung va hanh', 'Minh se tim mon phu hop voi nguyen lieu nay.'),
    ('budget', 'Toi co 100k cho bua toi', 'Minh se loc mon trong ngan sach nay.'),
    ('recipe', 'Cach lam mon nay nhu the nao', 'Minh se mo ta tung buoc che bien.'),
    ('shopping', 'Tao danh sach mua sam cho bua an', 'Minh se tong hop danh sach can mua.'),
]

# ============================================================================
# SEEDING FUNCTIONS
# ============================================================================

def seed_foods():
    """Seed food data into database."""
    print("\n" + "=" * 70)
    print("SEEDING FOODS")
    print("=" * 70)
    
    created_count = 0
    skipped_count = 0
    
    for food_data in FOODS_DATA:
        try:
            defaults = {key: value for key, value in food_data.items() if key != 'serving_size'}
            # Ensure category is a FoodCategory instance
            category_name = food_data.get('category')
            if category_name:
                cat, _ = FoodCategory.objects.get_or_create(name=category_name)
                defaults['category'] = cat

            food, created = Food.objects.get_or_create(
                name=food_data['name'],
                defaults=defaults
            )
            if created:
                created_count += 1
                print(f"  [OK] {food.name}")
            else:
                skipped_count += 1
        except Exception as e:
            print(f"  [ERROR] {food_data['name']}: {str(e)}")
    
    print(f"\n  • Created: {created_count} foods")
    print(f"  • Skipped: {skipped_count} foods (already exist)")
    print(f"  • Total: {Food.objects.count()} foods in database")
    return created_count

def seed_intents():
    """Seed chat intents into database."""
    print("\n" + "=" * 70)
    print("SEEDING INTENTS")
    print("=" * 70)
    
    created_count = 0
    
    for intent_data in INTENTS_DATA:
        try:
            intent, created = Intent.objects.get_or_create(
                name=intent_data['name'],
                defaults={
                    'topic': intent_data['topic'],
                    'description': intent_data['description']
                }
            )
            if created:
                created_count += 1
                print(f"  [OK] {intent.name}: {intent.topic}")
        except Exception as e:
            print(f"  [ERROR] {intent_data['name']}: {str(e)}")
    
    print(f"\n  • Created: {created_count} intents")
    print(f"  • Total: {Intent.objects.count()} intents in database")
    return created_count

def seed_intent_patterns():
    """Seed intent patterns for NLU."""
    print("\n" + "=" * 70)
    print("SEEDING INTENT PATTERNS")
    print("=" * 70)
    
    created_count = 0
    skipped_count = 0
    intent_lookup = {intent.name: intent for intent in Intent.objects.all()}
    
    for pattern_data in INTENT_PATTERNS_DATA:
        try:
            intent = intent_lookup.get(pattern_data['intent'])
            if not intent:
                continue
            pattern, created = Pattern.objects.get_or_create(
                intent=intent,
                text=pattern_data['pattern'],
                defaults={
                    # Retain the richer AI training metadata on the modern chat pattern table only.
                }
            )
            if created:
                created_count += 1
                print(f"  [OK] {pattern_data['intent']:25} | '{pattern_data['pattern']}'")
            else:
                skipped_count += 1
        except Exception as e:
            print(f"  [ERROR] {pattern_data['intent']} | {pattern_data['pattern']}: {str(e)}")
    
    print(f"\n  • Created: {created_count} patterns")
    print(f"  • Skipped: {skipped_count} patterns (already exist)")
    print(f"  • Total: {Pattern.objects.count()} patterns in database")
    return created_count


def seed_message_intents():
    """Seed labeled chat messages for intent learning."""
    print("\n" + "=" * 70)
    print("SEEDING MESSAGE INTENTS")
    print("=" * 70)

    account, _ = Account.objects.get_or_create(
        username='intent_seed_user',
        defaults={
            'email': 'intent_seed_user@example.local',
            'password_hash': 'seed_placeholder_hash',
            'role': 'user',
            'is_active': True,
        },
    )

    UserProfile.objects.get_or_create(
        account=account,
        defaults={
            'name': 'Intent Seed User',
            'age': 30,
            'gender': 'other',
            'activity_level': 'moderate',
            'health_goal': 'maintain',
            'dietary_preferences': 'balanced',
            'medical_conditions': 'none',
        },
    )

    session, _ = ChatSession.objects.get_or_create(
        account=account,
        title='[SeedIntent] training session',
        defaults={'ask_count': 0, 'missing_fields': [], 'filled_fields': {}},
    )
    MessageIntent.objects.filter(message__session=session).delete()
    ChatMessage.objects.filter(session=session).delete()

    intent_lookup = {intent.name: intent for intent in Intent.objects.all()}
    created_count = 0

    for index, (intent_name, user_text, assistant_text) in enumerate(MESSAGE_INTENT_SAMPLES, start=1):
        intent = intent_lookup.get(intent_name)
        if not intent:
            continue

        user_msg = ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_text,
        )
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=assistant_text,
        )

        MessageIntent.objects.create(
            message=user_msg,
            intent=intent,
            confidence=0.95,
        )
        created_count += 1
        print(f"  [OK] {index:02d}. {intent_name}: {user_text}")

    print(f"\n  • Created: {created_count} labeled message samples")
    print(f"  • Total: {MessageIntent.objects.count()} message labels in database")
    return created_count

def seed_all():
    """Seed all data."""
    print("\n" + "=" * 70)
    print("SMART CHEF - CONSOLIDATED SEED DATA")
    print("=" * 70)
    
    try:
        foods_created = seed_foods()
        intents_created = seed_intents()
        patterns_created = seed_intent_patterns()
        message_intents_created = seed_message_intents()
        
        print("\n" + "=" * 70)
        print("SEED COMPLETE")
        print("=" * 70)
        print(f"  • Foods: {foods_created}")
        print(f"  • Intents: {intents_created}")
        print(f"  • Patterns: {patterns_created}")
        print(f"  • Message intents: {message_intents_created}")
        print(f"\n[SUCCESS] All seed data loaded successfully!")
        return True
    except Exception as e:
        print(f"\n[ERROR] Seed failed: {str(e)}")
        return False

# ============================================================================
# MAIN
# ============================================================================

def build_parser():
    parser = argparse.ArgumentParser(description='Seed data for Smart Chef')
    parser.add_argument('--foods', action='store_true', help='Seed only foods')
    parser.add_argument('--intents', action='store_true', help='Seed only intents')
    parser.add_argument('--patterns', action='store_true', help='Seed only intent patterns')
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.foods:
        seed_foods()
    elif args.intents:
        seed_intents()
    elif args.patterns:
        seed_intent_patterns()
    else:
        seed_all()


if __name__ == '__main__':
    main()
