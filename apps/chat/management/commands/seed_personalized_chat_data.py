from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.chat.models import ChatMessage, ChatSession, Intent, MessageIntent
from apps.users.models import Account, UserProfile


SEED_PREFIX = "[SeedPersonalized]"
DEFAULT_USERNAME = "personalized_seed_user"
SAMPLES_PER_INTENT = 30


INTENT_DEFINITIONS = [
    {
        "name": "meal_recommendation",
        "topic": "Personalized Food Suggestion",
        "description": "De xuat mon an theo ho so va so thich ca nhan",
        "prompt": "goi y bua an phu hop cho toi",
    },
    {
        "name": "nutrition_query",
        "topic": "Nutrition Details",
        "description": "Hoi thong tin dinh duong theo boi canh ca nhan",
        "prompt": "phan tich dinh duong cua bua an nay",
    },
    {
        "name": "calorie_tracking",
        "topic": "Calorie Tracking",
        "description": "Theo doi calo hang ngay theo muc tieu",
        "prompt": "hom nay toi da an bao nhieu calo",
    },
    {
        "name": "macro_balance",
        "topic": "Macro Balance",
        "description": "Can bang protein carbs fat theo profile",
        "prompt": "kiem tra ti le protein carbs fat cho toi",
    },
    {
        "name": "meal_plan_daily",
        "topic": "Daily Meal Plan",
        "description": "Lap thuc don 1 ngay theo ca nhan hoa",
        "prompt": "lap thuc don ca ngay cho toi",
    },
    {
        "name": "meal_plan_weekly",
        "topic": "Weekly Meal Plan",
        "description": "Lap thuc don 7 ngay theo dieu kien ca nhan",
        "prompt": "lap ke hoach bua an cho 7 ngay",
    },
    {
        "name": "budget_meals",
        "topic": "Budget Meals",
        "description": "Goi y bua an theo ngan sach ca nhan",
        "prompt": "goi y bua an tiet kiem theo ngan sach",
    },
    {
        "name": "ingredient_substitution",
        "topic": "Ingredient Substitution",
        "description": "Thay the nguyen lieu phu hop tinh trang nguoi dung",
        "prompt": "thay the nguyen lieu nay bang gi",
    },
    {
        "name": "cooking_method",
        "topic": "Cooking Method",
        "description": "Tu van cach che bien phu hop muc tieu suc khoe",
        "prompt": "che bien mon nay the nao cho lanh manh",
    },
    {
        "name": "disease_friendly_diet",
        "topic": "Medical Diet",
        "description": "Tu van an uong theo benh nen",
        "prompt": "toi co benh nen thi nen an gi",
    },
    {
        "name": "weight_loss_goal",
        "topic": "Weight Loss",
        "description": "Ke hoach an uong giam can ca nhan hoa",
        "prompt": "len thuc don giam can cho toi",
    },
    {
        "name": "muscle_gain_goal",
        "topic": "Muscle Gain",
        "description": "Ke hoach an uong tang co ca nhan hoa",
        "prompt": "goi y bua an ho tro tang co",
    },
    {
        "name": "shopping_list",
        "topic": "Shopping Assistant",
        "description": "Tao danh sach mua sam theo muc tieu cua user",
        "prompt": "tao danh sach mua sam cho bua an cua toi",
    },
    {
        "name": "leftovers_reuse",
        "topic": "Leftover Reuse",
        "description": "Tan dung do an con lai theo profile dinh duong",
        "prompt": "toi con do an thua thi nen lam mon gi",
    },
    {
        "name": "hydration_habit",
        "topic": "Hydration Guidance",
        "description": "Nhac nho va theo doi nuoc uong ca nhan",
        "prompt": "nhac toi uong nuoc theo lich",
    },
]


PERSONAL_CONTEXTS = [
    "toi la nhan vien van phong it van dong",
    "toi tap gym 4 buoi moi tuan",
    "toi hay ngu muon va an toi tre",
    "toi khong an cay va de day da day",
    "toi uu tien mon viet va nau nhanh",
    "toi dang theo doi duong huyet",
    "toi muon an dam nhung it dau mo",
    "toi hay di choi the thao cuoi tuan",
    "toi muon giu can nang on dinh",
    "toi can bua an gon nhe de mang di lam",
]

TIME_CONTEXTS = [
    "buoi sang",
    "buoi trua",
    "buoi chieu",
    "buoi toi",
    "sau khi tap",
    "truoc khi ngu",
]

GOAL_CONTEXTS = [
    "uu tien du protein",
    "giam bot duong",
    "giu tong calo hop ly",
    "de tieu hoa",
    "it natri",
    "tiet kiem chi phi",
]


class Command(BaseCommand):
    help = (
        "Seed personalized chat learning data into existing chat tables only. "
        "Creates >=15 intent types with >=30 samples each and 30-minute intervals."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", default=DEFAULT_USERNAME, help="Target account username")
        parser.add_argument(
            "--samples-per-intent",
            type=int,
            default=SAMPLES_PER_INTENT,
            help="Number of user-message samples per intent",
        )
        parser.add_argument(
            "--keep-existing",
            action="store_true",
            help="Do not remove existing personalized seed sessions for this user",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"]
        samples_per_intent = max(1, int(options["samples_per_intent"]))
        keep_existing = bool(options["keep_existing"])

        account, _ = Account.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@example.local",
                "password_hash": "seed_placeholder_hash",
                "role": "user",
                "is_active": True,
            },
        )

        UserProfile.objects.get_or_create(
            account=account,
            defaults={
                "name": "Personalized Seed User",
                "age": 30,
                "gender": "other",
                "activity_level": "moderate",
                "health_goal": "maintain",
                "dietary_preferences": "balanced",
                "medical_conditions": "none",
            },
        )

        if not keep_existing:
            old_sessions = ChatSession.objects.filter(account=account, title__startswith=SEED_PREFIX)
            old_count = old_sessions.count()
            old_messages = ChatMessage.objects.filter(session__in=old_sessions)
            MessageIntent.objects.filter(message__in=old_messages).delete()
            old_messages.delete()
            old_sessions.delete()
            self.stdout.write(self.style.WARNING(f"Removed {old_count} old personalized seed sessions."))

        intents = []
        for definition in INTENT_DEFINITIONS:
            intent, _ = Intent.objects.get_or_create(
                name=definition["name"],
                defaults={
                    "topic": definition["topic"],
                    "description": definition["description"],
                },
            )
            intents.append((intent, definition))

        total_samples = len(intents) * samples_per_intent
        start_time = timezone.now() - timedelta(minutes=30 * (total_samples + 10))

        created_sessions = 0
        created_user_messages = 0
        created_assistant_messages = 0
        created_labels = 0

        sample_index = 0
        for intent, definition in intents:
            session = ChatSession.objects.create(
                account=account,
                title=f"{SEED_PREFIX} {intent.name}",
                current_intent_id=intent.id,
                ask_count=0,
                missing_fields=[],
                filled_fields={},
            )
            ChatSession.objects.filter(pk=session.pk).update(
                created_at=start_time + timedelta(minutes=30 * sample_index),
                updated_at=start_time + timedelta(minutes=30 * sample_index),
            )
            created_sessions += 1

            for i in range(samples_per_intent):
                user_time = start_time + timedelta(minutes=30 * sample_index)
                assistant_time = user_time + timedelta(minutes=1)

                context = PERSONAL_CONTEXTS[(sample_index + i) % len(PERSONAL_CONTEXTS)]
                time_ctx = TIME_CONTEXTS[(sample_index + i) % len(TIME_CONTEXTS)]
                goal_ctx = GOAL_CONTEXTS[(sample_index + i) % len(GOAL_CONTEXTS)]

                user_content = (
                    f"[{intent.name}] Mau {i + 1}: {definition['prompt']}. "
                    f"Ho so ca nhan: {context}. Khung gio: {time_ctx}. Muc tieu: {goal_ctx}."
                )
                assistant_content = (
                    f"Phan hoi cho {intent.name} mau {i + 1}. "
                    f"He thong uu tien ca nhan hoa theo profile va muc tieu nguoi dung."
                )

                user_msg = ChatMessage.objects.create(
                    session=session,
                    role="user",
                    content=user_content,
                )
                ChatMessage.objects.filter(pk=user_msg.pk).update(created_at=user_time)
                created_user_messages += 1

                assistant_msg = ChatMessage.objects.create(
                    session=session,
                    role="assistant",
                    content=assistant_content,
                )
                ChatMessage.objects.filter(pk=assistant_msg.pk).update(created_at=assistant_time)
                created_assistant_messages += 1

                MessageIntent.objects.create(
                    message=user_msg,
                    intent=intent,
                    confidence=0.95,
                )
                created_labels += 1

                sample_index += 1

        self.stdout.write(self.style.SUCCESS("Personalized chat seed completed."))
        self.stdout.write(f"Account: {account.username} (id={account.id})")
        self.stdout.write(f"Intent types: {len(intents)}")
        self.stdout.write(f"Samples per intent: {samples_per_intent}")
        self.stdout.write(f"Created sessions: {created_sessions}")
        self.stdout.write(f"Created user messages: {created_user_messages}")
        self.stdout.write(f"Created assistant messages: {created_assistant_messages}")
        self.stdout.write(f"Created message labels: {created_labels}")
