import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noi_tro_ai.settings')
django.setup()

from app.models import Food, UserProfile

foods_data = [
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

if Food.objects.count() == 0:
    for f in foods_data:
        Food.objects.create(**f)
    print(f"Da them {len(foods_data)} mon an vao CSDL")
else:
    print(f"Da co {Food.objects.count()} mon an trong CSDL, bo qua seed")

if UserProfile.objects.count() == 0:
    UserProfile.objects.create(
        name="Nguoi dung",
        age=30,
        weight=60,
        height=165,
        gender="Nam",
        health_goal="An uong lanh manh",
        activity_level="Van dong vua",
        daily_calorie_target=2000,
    )
    print("Da tao ho so nguoi dung mac dinh")
else:
    print("Da co ho so nguoi dung, bo qua")

print("Hoan tat seed du lieu!")
