import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','smart_chef.settings')
import django
django.setup()
from app.services.external_apis import _gemini_generate_text
from app.services.nutrition_data_service import NutritionDataFiller
from apps.nutrition.models import Ingredient

ing = Ingredient.objects.filter(id=2).first()
if not ing:
    print('Ingredient id=2 not found')
    raise SystemExit(1)

print('Ingredient:', ing.name)
prompt = (
    'Bạn là chuyên gia dinh dưỡng. Hãy ước tính dinh dưỡng cho nguyên liệu sau theo 100g. '
    'Chỉ trả về JSON hợp lệ với các khóa calories, protein, carbs, fat, fiber.\\n\\n'
    f'Nguyên liệu: {ing.name}\\n'
    'Nếu có mô tả hoặc tên tiếng Việt mơ hồ, vẫn hãy suy luận theo nguyên liệu phổ biến tương ứng.'
)
try:
    text = _gemini_generate_text(prompt, system_instruction='Ban la chuyen gia dinh duong. Chi tra ve JSON hop le.', max_output_tokens=512)
    print('\nGemini returned:\n', text)
    payload = NutritionDataFiller._extract_json_payload(text)
    print('\nParsed payload:\n', payload)
except Exception as e:
    print('Gemini call error:', e)
    raise
