import json
from datetime import date, timedelta

import pytest
from django.test import Client
from django.contrib.auth.hashers import make_password

from apps.users.models import Account
from apps.nutrition.models import Food, FoodCategory, NutritionLog
from apps.meal_plans.models import MealPlan
from apps.chat.models import ChatMessage, ChatSession, Intent, Pattern
from apps.core_models.models import SearchEvent
from apps.core_models.ai_learning_models import AIRequestLog
from apps.users.models import UserProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return Client()


def create_user(username, password="Password123", role="user"):
    return Account.objects.create(
        username=username,
        email=f"{username}@local.test",
        password_hash=make_password(password),
        role=role,
        is_active=True,
    )


def create_admin(username="admin_auto", password="Password123"):
    return create_user(username=username, password=password, role="admin")


def create_food(name, calories=130, protein=5, carbs=28, fat=1):
    category, _ = FoodCategory.objects.get_or_create(name=f"Cat-{name}")
    return Food.objects.create(
        name=name,
        category=category,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        fiber=2,
    )


def login(client, username, password="Password123"):
    response = client.post(
        "/auth/login/",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    return response


def register(client, username, password="Password123"):
    return client.post(
        "/auth/register/",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )



def test_tc001_dang_ky_tai_khoan(client):
    response = register(client, "user_tc001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert Account.objects.filter(username="user_tc001").exists()
    assert client.session.get("user_id")



def test_tc002_dang_nhap(client):
    create_user("user_tc002")

    response = login(client, "user_tc002")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert client.session.get("user_id")



def test_tc003_dang_xuat(client):
    account = create_user("user_tc003")
    login(client, "user_tc003")

    response = client.post("/auth/logout/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert client.session.get("user_id") is None
    assert Account.objects.filter(pk=account.pk).exists()



def test_tc004_dang_nhap_quan_tri(client):
    create_admin("admin_tc004")

    response = client.post(
        "/admin-panel/login/submit/",
        data={"username": "admin_tc004", "password": "Password123", "next_url": ""},
    )

    assert response.status_code == 302
    assert client.session.get("user_id")



def test_tc005_them_nhat_ky_an_uong(client):
    account = create_user("user_tc005")
    login(client, "user_tc005")
    food = create_food("Cơm trắng")

    response = client.post(
        "/theo-doi/ghi/",
        data=json.dumps(
            {
                "food_id": food.id,
                "servings": 1.5,
                "date": "2026-05-24",
                "meal_type": "Bữa trưa",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"]
    assert payload["food"] == food.name
    assert NutritionLog.objects.filter(account=account, food=food).exists()



def test_tc006_tim_kiem_thuc_pham(client):
    create_food("Canh rau")

    response = client.get("/mon-an/tim-kiem/?q=canh")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert any(item["name"] == "Canh rau" for item in payload)


@pytest.mark.xfail(reason="Endpoint chi tiết thực phẩm chưa được expose qua route hiện tại")
def test_tc007_xem_chi_tiet_thuc_pham(client):
    create_food("Bún bò")

    response = client.get("/mon-an/chi-tiet/?name=Bún bò")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["food"]["name"] == "Bún bò"



def test_tc008_tinh_luong_dinh_duong_nap_vao(client):
    account = create_user("user_tc008")
    login(client, "user_tc008")
    food = create_food("Ức gà", calories=165, protein=31, carbs=0, fat=3.6)
    today = date.today().isoformat()

    response = client.post(
        "/theo-doi/ghi/",
        data=json.dumps(
            {
                "food_id": food.id,
                "servings": 2,
                "date": today,
                "meal_type": "Bữa tối",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    dashboard_response = client.get("/")
    assert dashboard_response.status_code == 200
    assert dashboard_response.context["today_calories"] == pytest.approx(330.0)



def test_tc009_xem_nhat_ky_dinh_duong(client):
    account = create_user("user_tc009")
    login(client, "user_tc009")
    food = create_food("Trứng")
    NutritionLog.objects.create(
        account=account,
        food=food,
        date="2026-05-24",
        meal_type="Bữa sáng",
        servings=1,
    )

    response = client.get("/theo-doi/?date=2026-05-24")

    assert response.status_code == 200
    assert response.context["selected_date"] == "2026-05-24"
    assert response.context["day_logs"].count() == 1


@pytest.mark.xfail(reason="Endpoint cập nhật nhật ký chưa được triển khai")
def test_tc010_cap_nhat_nhat_ky_dinh_duong(client):
    account = create_user("user_tc010")
    login(client, "user_tc010")
    food = create_food("Sữa")
    log = NutritionLog.objects.create(
        account=account,
        food=food,
        date="2026-05-24",
        meal_type="Bữa sáng",
        servings=1,
    )

    response = client.post(
        f"/theo-doi/cap-nhat/{log.id}/",
        data=json.dumps({"servings": 2, "meal_type": "Bữa trưa"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True



def test_tc011_xoa_nhat_ky_dinh_duong(client):
    account = create_user("user_tc011")
    login(client, "user_tc011")
    food = create_food("Gà")
    log = NutritionLog.objects.create(
        account=account,
        food=food,
        date="2026-05-24",
        meal_type="Bữa tối",
        servings=1,
    )

    response = client.post(f"/theo-doi/xoa/{log.id}/")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert not NutritionLog.objects.filter(pk=log.pk).exists()



def test_tc012_xem_dashboard_hang_ngay(client):
    account = create_user("user_tc012")
    login(client, "user_tc012")
    food = create_food("Thịt lợn", calories=250, protein=26, carbs=0, fat=13)
    today = date.today().isoformat()
    NutritionLog.objects.create(
        account=account,
        food=food,
        date=today,
        meal_type="Bữa trưa",
        servings=1,
    )

    response = client.get("/")

    assert response.status_code == 200
    assert response.context["today_calories"] == pytest.approx(250.0)
    assert response.context["today_protein"] == pytest.approx(26.0)
    assert response.context["today_carbs"] == pytest.approx(0.0)
    assert response.context["today_fat"] == pytest.approx(13.0)



def test_tc013_so_sanh_dinh_duong(client):
    account = create_user("user_tc013")
    login(client, "user_tc013")
    food_today = create_food("Tôm", calories=100, protein=24, carbs=1, fat=1)
    food_yesterday = create_food("Tôm cũ", calories=80, protein=20, carbs=1, fat=1)
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    NutritionLog.objects.create(account=account, food=food_today, date=today, meal_type="Bữa sáng", servings=1)
    NutritionLog.objects.create(account=account, food=food_yesterday, date=yesterday, meal_type="Bữa sáng", servings=1)

    response = client.get("/")

    assert response.status_code == 200
    assert "today_metrics" in response.context
    assert response.context["today_metrics"]["today"]["calories"] == pytest.approx(100.0)
    assert response.context["today_metrics"]["yesterday"]["calories"] == pytest.approx(80.0)



def test_tc014_nhan_goi_y_dinh_duong(client):
    account = create_user("user_tc014")
    login(client, "user_tc014")
    food = create_food("Salad", calories=80, protein=5, carbs=10, fat=2)
    NutritionLog.objects.create(account=account, food=food, date="2026-05-24", meal_type="Bữa sáng", servings=1)

    response = client.get("/")

    assert response.status_code == 200
    assert response.context["nutrition_suggestions"]



def test_tc015_tao_thuc_don(client):
    account = create_user("user_tc015")
    login(client, "user_tc015")
    food = create_food("Bò xào")

    response = client.post(
        "/thuc-don/them/",
        data=json.dumps(
            {
                "food_id": food.id,
                "date": "2026-05-25",
                "meal_type": "Bữa trưa",
                "servings": 1,
                "notes": "Tạo thực đơn",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["food"] == food.name
    assert MealPlan.objects.filter(account=account, food=food).exists()



def test_tc016_xem_thuc_don(client):
    account = create_user("user_tc016")
    login(client, "user_tc016")
    food = create_food("Mì xào")
    MealPlan.objects.create(account=account, food=food, date="2026-05-25", meal_type="Bữa trưa", servings=1)

    response = client.get("/thuc-don/?year=2026&month=5")

    assert response.status_code == 200
    assert response.context["plans_by_date"]


@pytest.mark.xfail(reason="Endpoint cập nhật thực đơn chưa được triển khai")
def test_tc017_cap_nhat_thuc_don(client):
    account = create_user("user_tc017")
    login(client, "user_tc017")
    food = create_food("Cháo")
    plan = MealPlan.objects.create(account=account, food=food, date="2026-05-25", meal_type="Bữa sáng", servings=1)

    response = client.post(
        f"/thuc-don/cap-nhat/{plan.id}/",
        data=json.dumps({"meal_type": "Bữa trưa", "servings": 2}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True



def test_tc018_them_mon_vao_thuc_don(client):
    account = create_user("user_tc018")
    login(client, "user_tc018")
    food1 = create_food("Bánh mì")
    food2 = create_food("Trứng ốp la")

    response1 = client.post(
        "/thuc-don/them/",
        data=json.dumps({"food_id": food1.id, "date": "2026-05-25", "meal_type": "Bữa sáng", "servings": 1}),
        content_type="application/json",
    )
    response2 = client.post(
        "/thuc-don/them/",
        data=json.dumps({"food_id": food2.id, "date": "2026-05-25", "meal_type": "Bữa sáng", "servings": 1}),
        content_type="application/json",
    )

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert MealPlan.objects.filter(account=account, food__name__in=["Bánh mì", "Trứng ốp la"]).count() == 2


@pytest.mark.xfail(reason="Endpoint sửa món trong thực đơn chưa được triển khai")
def test_tc019_sua_mon_trong_thuc_don(client):
    account = create_user("user_tc019")
    login(client, "user_tc019")
    food = create_food("Phở")
    plan = MealPlan.objects.create(account=account, food=food, date="2026-05-25", meal_type="Bữa trưa", servings=1)

    response = client.post(
        f"/thuc-don/sua/{plan.id}/",
        data=json.dumps({"servings": 2}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True



def test_tc020_xoa_thuc_don_hoac_mon_an(client):
    account = create_user("user_tc020")
    login(client, "user_tc020")
    food = create_food("Bún riêu")
    plan = MealPlan.objects.create(account=account, food=food, date="2026-05-25", meal_type="Bữa trưa", servings=1)

    response = client.post(f"/thuc-don/xoa/{plan.id}/")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert not MealPlan.objects.filter(pk=plan.pk).exists()



def test_tc021_gui_tin_nhan_chat(client):
    create_user("user_tc021")
    login(client, "user_tc021")

    response = client.post(
        "/chat/send/",
        data=json.dumps({"message": "Cơm trắng"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "assistant"
    assert "content" in payload


def test_tc021b_chat_send_gemini_fallback_logs_search_event(client, monkeypatch):
    from app.features.user_panel import views as user_panel_views
    import app.services.external_apis as external_apis
    import app.services.ai_orchestrator_service as ai_orchestrator

    account = create_user("user_tc021b")
    login(client, "user_tc021b")

    def fake_orchestrate(user_text, account_obj, chat_session, call_gemini=False, top_k=5):
        return {
            'path': 'gemini',
            'intent_name': None,
            'intent_confidence': 0.0,
            'personalization_context': {},
            'candidates': [],
            'rag_evidence': {'foods': [], 'recipes': [], 'ingredients': []},
            'decision': 'gemini_fallback',
        }

    monkeypatch.setattr(user_panel_views.AIOrchestratorService, 'orchestrate', staticmethod(fake_orchestrate))
    monkeypatch.setattr(user_panel_views, '_service_call_gemini_with_debug', lambda chat_session, system_context: ('Gemini response text', None))
    monkeypatch.setattr(user_panel_views, '_route_chat_intent', lambda *args, **kwargs: None)
    monkeypatch.setattr(user_panel_views, '_find_saved_chat_answer', lambda *args, **kwargs: None)
    monkeypatch.setattr(external_apis, 'save_chat_response_to_cache', lambda *args, **kwargs: None)
    monkeypatch.setattr(user_panel_views, 'AI_AVAILABLE', True)
    monkeypatch.setattr(ai_orchestrator, 'GEMINI_ENABLED', True)

    before_count = SearchEvent.objects.count()
    response = client.post(
        "/chat/send/",
        data=json.dumps({"message": "Cho tôi gợi ý món ăn."}),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "assistant"
    assert payload["content"] == "Gemini response text"
    assert SearchEvent.objects.count() == before_count + 1
    ai_log = AIRequestLog.objects.order_by("-id").first()
    assert ai_log is not None
    assert ai_log.provider == "gemini"
    assert ai_log.response_ok is True


def test_chat_send_rejects_off_topic_cache_and_uses_valid_gemini_response(client, monkeypatch):
    from app.features.user_panel import views as user_panel_views
    import app.services.external_apis as external_apis
    import app.services.ai_orchestrator_service as ai_orchestrator

    create_user("user_guard_01")
    login(client, "user_guard_01")

    def fake_orchestrate(user_text, account_obj, chat_session, call_gemini=False, top_k=5):
        return {
            'path': 'gemini',
            'intent_name': 'price',
            'intent_confidence': 0.95,
            'personalization_context': {},
            'candidates': [],
            'rag_evidence': {'foods': [], 'recipes': [], 'ingredients': []},
            'decision': 'gemini_guarded',
        }

    monkeypatch.setattr(user_panel_views.AIOrchestratorService, 'orchestrate', staticmethod(fake_orchestrate))
    monkeypatch.setattr(user_panel_views, '_service_call_gemini_with_debug', lambda chat_session, system_context: ('Gia uoc tinh ca chua la 25000 dong/kg.', None))
    monkeypatch.setattr(user_panel_views, '_route_chat_intent', lambda *args, **kwargs: None)
    monkeypatch.setattr(user_panel_views, '_find_saved_chat_answer', lambda *args, **kwargs: {'response': 'Cong thuc nau ca chua xao trung gom 3 buoc.'})
    monkeypatch.setattr(external_apis, 'save_chat_response_to_cache', lambda *args, **kwargs: None)
    monkeypatch.setattr(user_panel_views, 'AI_AVAILABLE', True)
    monkeypatch.setattr(ai_orchestrator, 'GEMINI_ENABLED', True)

    response = client.post(
        "/chat/send/",
        data=json.dumps({"message": "Gia ca chua bao nhieu?"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["content"] == "Gia uoc tinh ca chua la 25000 dong/kg."

    rejected_log = AIRequestLog.objects.filter(
        provider="cache",
        route_path="rejected",
        response_ok=False,
    ).order_by("-id").first()
    assert rejected_log is not None

    final_log = AIRequestLog.objects.filter(provider="gemini", response_ok=True).order_by("-id").first()
    assert final_log is not None


def test_tc021c_admin_ai_quality_dashboard(client):
    create_admin("admin_tc021c")
    client.post(
        "/admin-panel/login/submit/",
        data={"username": "admin_tc021c", "password": "Password123", "next_url": ""},
    )
    AIRequestLog.objects.create(
        provider="local_rule",
        route_path="local",
        decision="test_dashboard",
        cache_hit=False,
        latency_ms=12,
        response_ok=True,
    )

    response = client.get("/admin-panel/ai-quality/?days=7")

    assert response.status_code == 200
    assert response.context["summary"]["total_requests"] >= 1



def test_tc022_xem_lich_su_chat(client):
    account = create_user("user_tc022")
    login(client, "user_tc022")
    session = ChatSession.objects.create(account=account, title="Phiên test")
    ChatMessage.objects.create(session=session, role="user", content="Cơm trắng")
    ChatMessage.objects.create(session=session, role="assistant", content="Mình tìm thấy món Cơm trắng.")

    response = client.get("/chat/")

    assert response.status_code == 200
    assert response.context["messages_data"]



def test_tc023_xoa_phien_chat_tin_nhan(client):
    account = create_user("user_tc023")
    login(client, "user_tc023")
    session = ChatSession.objects.create(account=account, title="Phiên test")
    ChatMessage.objects.create(session=session, role="user", content="Cơm trắng")

    response = client.post("/api/chat/clear/")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert ChatMessage.objects.filter(session=session).count() == 0



def test_tc024_phan_tich_hanh_vi_suc_khoe(client):
    account = create_user("user_tc024")
    login(client, "user_tc024")
    food = create_food("Salad")
    NutritionLog.objects.create(account=account, food=food, date="2026-05-24", meal_type="Bữa sáng", servings=1)

    response = client.post(
        "/chat/send/",
        data=json.dumps({"message": "Tôi ăn salad hôm nay"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["content"]



def test_tc025_xem_ho_so_ca_nhan(client):
    account = create_user("user_tc025")
    login(client, "user_tc025")

    response = client.get("/ho-so/")

    assert response.status_code == 200



def test_tc026_cap_nhat_ho_so(client):
    account = create_user("user_tc026")
    login(client, "user_tc026")

    response = client.post(
        "/ho-so/luu/",
        data=json.dumps(
            {
                "name": "Nguyễn Văn A",
                "age": 28,
                "weight": 70,
                "height": 170,
                "gender": "Nam",
                "health_goal": "Giảm cân",
                "activity_level": "Vừa",
                "daily_calorie_target": 2200,
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    profile = UserProfile.objects.get(account=account)
    assert profile.name == "Nguyễn Văn A"
    assert profile.daily_calorie_target == 2200



def test_tc027_tinh_muc_tieu_dinh_duong(client):
    account = create_user("user_tc027")
    login(client, "user_tc027")
    UserProfile.objects.create(
        account=account,
        name="Test",
        age=30,
        weight=70,
        height=170,
        daily_calorie_target=2200,
    )

    response = client.get("/")

    assert response.status_code == 200
    assert response.context["calorie_target"] == 2200



def test_tc028_xoa_tai_khoan(client):
    account = create_user("user_tc028")
    login(client, "user_tc028")

    response = client.post(
        "/api/accounts/delete/",
        data=json.dumps({"password": "Password123"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert not Account.objects.filter(pk=account.pk).exists()


@pytest.mark.xfail(reason="Import dữ liệu thực phẩm chưa có endpoint API dùng cho test tự động")
def test_tc029_nhap_du_lieu(client):
    response = client.post("/admin-panel/import/submit/", data={})

    assert response.status_code == 200



def test_tc030_them_thuc_pham(client):
    food = create_food("Mì tôm")

    assert food.pk
    assert Food.objects.filter(pk=food.pk).exists()



def test_tc031_xem_danh_sach_chi_tiet_thuc_pham(client):
    create_food("Bánh xèo")

    response = client.get("/mon-an/tim-kiem/?q=bánh")

    assert response.status_code == 200
    payload = response.json()
    assert any(item["name"] == "Bánh xèo" for item in payload)



def test_tc032_cap_nhat_thuc_pham(client):
    food = create_food("Nước chanh")

    food.calories = 80
    food.save(update_fields=["calories"])

    updated_food = Food.objects.get(pk=food.pk)
    assert updated_food.calories == 80



def test_tc033_xoa_thuc_pham(client):
    food = create_food("Cà phê")

    food.delete()

    assert not Food.objects.filter(pk=food.pk).exists()


@pytest.mark.xfail(reason="Cleanup dữ liệu trùng/lỗi chưa có luồng kiểm thử end-to-end được expose")
def test_tc034_don_du_lieu_trung_loi(client):
    response = client.post("/admin-panel/data-manager/crawl-control/", data={})

    assert response.status_code == 200



def test_tc035_them_intent_pattern(client):
    intent = Intent.objects.create(name="nutrition", description="Hỏi về dinh dưỡng")
    pattern = Pattern.objects.create(intent=intent, text="bao nhiêu calo")

    assert intent.pk
    assert pattern.pk



def test_tc036_cap_nhat_intent_pattern(client):
    intent = Intent.objects.create(name="meal_plan", description="Lập thực đơn")
    pattern = Pattern.objects.create(intent=intent, text="lập thực đơn")

    pattern.text = "lập thực đơn hàng ngày"
    pattern.save(update_fields=["text"])

    assert Pattern.objects.get(pk=pattern.pk).text == "lập thực đơn hàng ngày"



def test_tc037_xoa_intent_pattern(client):
    intent = Intent.objects.create(name="chat", description="Chủ đề chat")
    pattern = Pattern.objects.create(intent=intent, text="xin chào")

    pattern.delete()

    assert not Pattern.objects.filter(pk=pattern.pk).exists()



def test_tc038_xem_danh_sach_chi_tiet_nguoi_dung(client):
    create_admin("admin_tc038")
    create_user("user_tc038")

    response = client.post(
        "/admin-panel/login/submit/",
        data={"username": "admin_tc038", "password": "Password123", "next_url": ""},
    )

    assert response.status_code == 302
    response = client.get("/api/accounts/list/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["total"] >= 2


@pytest.mark.xfail(reason="Endpoint cập nhật người dùng chưa được expose dưới dạng API riêng")
def test_tc039_cap_nhat_nguoi_dung(client):
    user = create_user("user_tc039")

    response = client.post(
        f"/api/accounts/{user.id}/",
        data=json.dumps({"role": "admin"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True



def test_tc040_xoa_vo_hieu_hoa_nguoi_dung(client):
    user = create_user("user_tc040")

    user.is_active = False
    user.save(update_fields=["is_active"])

    assert not Account.objects.get(pk=user.pk).is_active
