import csv
import io
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.http import HttpResponse
from django.urls import reverse

from apps.users.models import (
    Account,
    UserGoal,
    UserFeedback,
    UserBehaviorLog,
    Disease,
    UserDisease,
    DiseaseNutritionRule,
    UserProfile,
    UserPreferenceProfile,
)
from apps.nutrition.models import (
    Food,
    FoodCategory,
    FoodIngredient,
    FoodPopularity,
    Ingredient,
    IngredientNutrition,
    IngredientPrice,
    IngredientAlias,
    Recipe,
    NutritionLog,
    DailyNutritionSummary,
    UnitConversion,
    ShoppingList,
)
from apps.meal_plans.models import MealPlan
from apps.chat.models import (
    ChatMessage,
    ChatResponseCache,
    ChatSession,
    ChatSummary,
    Intent,
    IntentEmbedding,
    MessageIntent,
    Pattern,
)
from apps.core_models.models import (
    AIRecommendation,
    SearchEvent,
)


# GHI NHO QUAN TRONG:
# Toan bo logic Data Manager va CSV cua admin duoc gom vao file nay.
# Muc tieu: tach rieng theo doi tuong Admin de app/views.py gon va de bao tri hon.

ADMIN_MODEL_GROUPS = {
    'system': {
        'label': 'He thong',
        'models': {'Account', 'ChatSession', 'ChatMessage', 'ChatSummary', 'ChatResponseCache'},
    },
    'profile': {
        'label': 'Nguoi dung',
        'models': {'UserProfile', 'UserGoal', 'UserFeedback', 'UserBehaviorLog', 'UserPreferenceProfile', 'UserDisease', 'Disease', 'DiseaseNutritionRule'},
    },
    'food': {
        'label': 'Thuc pham',
        'models': {'Food', 'FoodCategory', 'FoodPopularity', 'Ingredient', 'IngredientNutrition', 'IngredientPrice', 'FoodIngredient', 'UnitConversion', 'Recipe'},
    },
    'nutrition': {
        'label': 'Dinh duong',
        'models': {'NutritionLog', 'DailyNutritionSummary', 'MealPlan'},
    },
    'ml': {
        'label': 'AI / ML',
        'models': {'Intent', 'Pattern', 'MessageIntent', 'IntentEmbedding', 'AIRecommendation', 'SearchEvent'},
    },
}

ADMIN_MODELS = [
    ('Account', 'Accounts', Account),
    ('ChatMessage', 'Chat messages', ChatMessage),
    ('ChatResponseCache', 'Chat response cache', ChatResponseCache),
    ('ChatSession', 'Chat sessions', ChatSession),
    ('ChatSummary', 'Chat summaries', ChatSummary),
    ('DailyNutritionSummary', 'Daily nutrition summary', DailyNutritionSummary),
    ('Disease', 'Diseases', Disease),
    ('DiseaseNutritionRule', 'Disease nutrition rules', DiseaseNutritionRule),
    ('Food', 'Foods', Food),
    ('FoodCategory', 'Food categories', FoodCategory),
    ('FoodIngredient', 'Food ingredients', FoodIngredient),
    ('FoodPopularity', 'Food popularity', FoodPopularity),
    ('Ingredient', 'Ingredients', Ingredient),
    ('IngredientNutrition', 'Ingredient nutrition', IngredientNutrition),
    ('IngredientPrice', 'Ingredient prices', IngredientPrice),
    ('Intent', 'Intents', Intent),
    ('IntentEmbedding', 'Intent embeddings', IntentEmbedding),
    ('MealPlan', 'Meal plans', MealPlan),
    ('MessageIntent', 'Message intents', MessageIntent),
    ('NutritionLog', 'Nutrition logs', NutritionLog),
    ('Pattern', 'Patterns', Pattern),
    ('Recipe', 'Recipes', Recipe),
    ('SearchEvent', 'Search events', SearchEvent),
    ('UnitConversion', 'Unit conversions', UnitConversion),
    ('UserBehaviorLog', 'User behavior logs', UserBehaviorLog),
    ('UserDisease', 'User diseases', UserDisease),
    ('UserFeedback', 'User feedback', UserFeedback),
    ('UserGoal', 'User goals', UserGoal),
    ('UserPreferenceProfile', 'User preference profiles', UserPreferenceProfile),
    ('UserProfile', 'User profiles', UserProfile),
    ('AIRecommendation', 'AI recommendations', AIRecommendation),
]

ADMIN_MODEL_LOOKUP = {key: (label, model) for key, label, model in ADMIN_MODELS}


def _resolve_row_preview_fields(model):
    priority_fields = ['id', 'name', 'title', 'username', 'email', 'role', 'content', 'date', 'meal_type', 'created_at']
    fields = []
    for field in model._meta.fields:
        if field.name in priority_fields:
            fields.append(field.name)
        if len(fields) >= 5:
            break
    if not fields:
        fields = [f.name for f in model._meta.fields[:5]]
    return fields


def _recent_count(model, days=7):
    since_date = date.today() - timedelta(days=days - 1)
    field_names = {field.name for field in model._meta.fields}
    if 'created_at' in field_names:
        return model.objects.filter(created_at__date__gte=since_date).count()
    if 'date' in field_names:
        return model.objects.filter(date__gte=since_date).count()
    return 0


def _serialize_value(value):
    if value is None:
        return ''
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _get_selected_models(group_key, query_text):
    query_text = (query_text or '').strip().lower()
    selected = []
    for key, label, model in ADMIN_MODELS:
        if group_key != 'all':
            group_info = ADMIN_MODEL_GROUPS.get(group_key)
            if not group_info or key not in group_info['models']:
                continue
        haystack = f'{key} {label} {model._meta.model_name}'.lower()
        if query_text and query_text not in haystack:
            continue
        selected.append((key, label, model))
    return selected


def _admin_card_payload(key, label, model):
    queryset = model.objects.all()
    row_count = queryset.count()
    field_names = _resolve_row_preview_fields(model)
    sample_rows = []
    latest_record = None
    schema_note = ''

    try:
        sample_rows = list(queryset.order_by('-pk').values(*field_names)[:5])
        latest_record = queryset.order_by('-pk').first()
    except DatabaseError:
        fallback_fields = [name for name in field_names if name not in {'id', model._meta.pk.name}]
        if not fallback_fields:
            fallback_fields = [field.name for field in model._meta.fields if field.name != 'id'][:5]
        try:
            sample_rows = list(queryset.values(*fallback_fields)[:5])
            latest_record = queryset.first()
            field_names = fallback_fields
            schema_note = 'Preview fallback due to legacy table schema mismatch.'
        except DatabaseError:
            sample_rows = []
            latest_record = None
            schema_note = 'Preview unavailable due to legacy table schema mismatch.'

    latest_snapshot = {}
    if latest_record:
        for field_name in field_names[:3]:
            latest_snapshot[field_name] = _serialize_value(getattr(latest_record, field_name, ''))

    preview_rows = []
    for row in sample_rows:
        preview_rows.append({
            'cells': [_serialize_value(row.get(field_name, '')) for field_name in field_names],
        })

    return {
        'key': key,
        'label': label,
        'model_name': model._meta.model_name,
        'count': row_count,
        'recent_7d': _recent_count(model, 7),
        'columns': field_names,
        'rows': preview_rows,
        'latest_snapshot': latest_snapshot,
        'schema_note': schema_note,
        'admin_url': f"/admin/app/{model._meta.model_name}/",
        'csv_url': f"/admin-panel/data-manager/export/{key}/",
        'manage_url': f"/admin-panel/data-manager/model/{key}/",
        'group': next((group_key for group_key, group in ADMIN_MODEL_GROUPS.items() if key in group['models']), 'other'),
    }


def _group_summaries(cards):
    result = []
    cards_by_key = {card['key']: card for card in cards}
    for group_key, group_info in ADMIN_MODEL_GROUPS.items():
        members = [cards_by_key[key] for key in group_info['models'] if key in cards_by_key]
        result.append({
            'key': group_key,
            'label': group_info['label'],
            'models': len(members),
            'rows': sum(item['count'] for item in members),
            'recent_7d': sum(item['recent_7d'] for item in members),
        })
    return result


def _admin_csv_response(model_label, model):
    _ = model_label
    field_names = [field.name for field in model._meta.fields]
    queryset = model.objects.all().order_by('-pk')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{model._meta.model_name}.csv"'
    writer = csv.writer(response)
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([_serialize_value(getattr(obj, field_name, '')) for field_name in field_names])
    return response


def _searchable_model_fields(model):
    result = []
    text_like_types = {
        'CharField',
        'TextField',
        'EmailField',
        'SlugField',
        'UUIDField',
    }
    for field in model._meta.fields:
        if field.get_internal_type() in text_like_types:
            result.append(field.name)
    return result


def _list_preview_fields(model, max_fields=7):
    priority = [
        model._meta.pk.name,
        'name',
        'title',
        'username',
        'email',
        'role',
        'date',
        'created_at',
    ]
    fields = []
    for name in priority:
        try:
            model._meta.get_field(name)
        except Exception:
            continue
        if name not in fields:
            fields.append(name)
        if len(fields) >= max_fields:
            return fields

    for field in model._meta.fields:
        if field.name not in fields:
            fields.append(field.name)
        if len(fields) >= max_fields:
            break
    return fields


def _safe_pk_value(value):
    if isinstance(value, (int, str)):
        return value
    return str(value)


def _serialize_row(obj, fields):
    return {field_name: _serialize_value(getattr(obj, field_name, '')) for field_name in fields}


def _dedupe_value(value):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return tuple(_dedupe_value(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, _dedupe_value(item)) for key, item in value.items()))
    return str(value)


def _dedupe_model_duplicates(model):
    fields = [field for field in model._meta.concrete_fields if not field.primary_key]
    if not fields:
        return {
            'checked_rows': 0,
            'duplicate_groups': 0,
            'deleted_rows': 0,
            'kept_rows': 0,
        }

    seen = {}
    duplicate_pks = []
    checked_rows = 0
    duplicate_groups = 0

    for obj in model.objects.all().order_by('pk').iterator():
        checked_rows += 1
        signature = tuple(_dedupe_value(getattr(obj, field.attname)) for field in fields)
        if signature in seen:
            duplicate_groups += 1
            duplicate_pks.append(obj.pk)
            continue
        seen[signature] = obj.pk

    deleted_rows = 0
    if duplicate_pks:
        with transaction.atomic():
            deleted_rows = model.objects.filter(pk__in=duplicate_pks).delete()[0]

    return {
        'checked_rows': checked_rows,
        'duplicate_groups': duplicate_groups,
        'deleted_rows': deleted_rows,
        'kept_rows': checked_rows - deleted_rows,
    }


def _clean_text_value(value):
    text = str(value or '').strip()
    return re.sub(r'\s+', ' ', text)


def _parse_bool_value(value):
    text = _clean_text_value(value).lower()
    if text in {'1', 'true', 'yes', 'y', 'on', 'co', 'có'}:
        return True
    if text in {'0', 'false', 'no', 'n', 'off', 'khong', 'không'}:
        return False
    raise ValueError('khong phai gia tri boolean hop le')


def _parse_decimal_value(value):
    text = _clean_text_value(value)
    text = re.sub(r'[^0-9,.\-]', '', text)
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif ',' in text:
        text = text.replace(',', '.')
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError('khong phai so thap phan hop le') from exc


def _parse_int_value(value):
    text = _clean_text_value(value)
    text = re.sub(r'[^0-9,.\-]', '', text)
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif ',' in text:
        text = text.replace(',', '.')
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError as exc:
        raise ValueError('khong phai so nguyen hop le') from exc


def _parse_float_value(value):
    text = _clean_text_value(value)
    text = re.sub(r'[^0-9,.\-]', '', text)
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif ',' in text:
        text = text.replace(',', '.')
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError('khong phai so thuc hop le') from exc


def _decode_uploaded_csv(uploaded_file):
    raw_bytes = uploaded_file.read()
    encodings = ['utf-8-sig', 'utf-8', 'cp1258', 'latin-1']
    last_error = None

    for encoding in encodings:
        try:
            return raw_bytes.decode(encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc

    raise ValueError(f'Khong doc duoc file CSV. Loi encoding: {last_error}')


def _detect_csv_dialect(csv_text):
    sample = csv_text[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=[',', ';', '\t', '|'])
    except csv.Error:
        return csv.excel


def _parse_date_value(value):
    text = _clean_text_value(value)
    if not text:
        return None
    candidates = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']
    for fmt in candidates:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError('khong phai dinh dang ngay hop le')


def _parse_datetime_value(value):
    text = _clean_text_value(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        pass
    candidates = ['%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M']
    for fmt in candidates:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError('khong phai dinh dang ngay-gio hop le')


def _parse_json_value(value):
    text = _clean_text_value(value)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if ',' in text:
            return [item.strip() for item in text.split(',') if item.strip()]
        return text


def _resolve_fk_instance(related_model, raw_value):
    text = _clean_text_value(raw_value)
    if not text:
        return None
    if text.isdigit():
        by_pk = related_model.objects.filter(pk=int(text)).first()
        if by_pk:
            return by_pk

    candidate_fields = ['username', 'email', 'name', 'title']
    for field_name in candidate_fields:
        try:
            related_model._meta.get_field(field_name)
        except Exception:
            continue
        candidate = related_model.objects.filter(**{f'{field_name}__iexact': text}).first()
        if candidate:
            return candidate
    return None


def _normalize_field_value(field, raw_value):
    text = _clean_text_value(raw_value)
    is_empty = text == ''

    if field.is_relation and getattr(field, 'many_to_one', False):
        if is_empty:
            if field.null:
                return None, None, []
            raise ValueError('truong lien ket bat buoc')
        related_obj = _resolve_fk_instance(field.related_model, text)
        if not related_obj:
            raise ValueError('khong tim thay ban ghi lien ket')
        return related_obj, None, []

    if is_empty:
        if field.null or field.blank or field.auto_created:
            return None, None, []
        if field.primary_key and field.auto_created:
            return None, None, []
        raise ValueError('truong bat buoc')

    field_type = field.get_internal_type()
    warnings = []

    if field_type in {'CharField', 'TextField', 'SlugField', 'UUIDField'}:
        return text, None, warnings

    if field_type == 'EmailField':
        return text.lower(), None, warnings

    if field_type in {'IntegerField', 'BigIntegerField', 'SmallIntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField'}:
        return _parse_int_value(text), None, warnings

    if field_type in {'FloatField'}:
        return _parse_float_value(text), None, warnings

    if field_type in {'DecimalField'}:
        return _parse_decimal_value(text), None, warnings

    if field_type in {'BooleanField', 'NullBooleanField'}:
        return _parse_bool_value(text), None, warnings

    if field_type == 'DateField':
        return _parse_date_value(text), None, warnings

    if field_type == 'DateTimeField':
        return _parse_datetime_value(text), None, warnings

    if field_type == 'JSONField':
        return _parse_json_value(text), None, warnings

    return text, None, warnings


def _csv_row_to_model_payload(model, raw_row, header_mapping=None):
    payload = {}
    errors = []
    warnings = []
    header_mapping = header_mapping or {}

    for field in model._meta.fields:
        if getattr(field, 'auto_created', False) and not getattr(field, 'primary_key', False):
            continue

        candidate_headers = []
        if field.name in header_mapping:
            candidate_headers.append(header_mapping[field.name])

        field_attname = getattr(field, 'attname', None)
        if field_attname and field_attname in header_mapping:
            candidate_headers.append(header_mapping[field_attname])

        candidate_headers.append(field.name)
        if field_attname and field_attname != field.name:
            candidate_headers.append(field_attname)

        csv_header = None
        for header in candidate_headers:
            if header in raw_row:
                csv_header = header
                break

        if not csv_header:
            continue

        row_value = raw_row.get(csv_header, None)

        if field.primary_key and field.auto_created and _clean_text_value(row_value) == '':
            continue

        try:
            normalized_value, _, field_warnings = _normalize_field_value(field, row_value)
            payload[field.name] = normalized_value
            for warning in field_warnings:
                warnings.append(f'{field.name}: {warning}')
        except Exception as exc:
            errors.append(f'{field.name}: {exc}')

    return payload, warnings, errors


def _get_all_models():
    return {
        'Account': Account,
        'UserProfile': UserProfile,
        'Food': Food,
        'Ingredient': Ingredient,
        'FoodIngredient': FoodIngredient,
        'Intent': Intent,
        'Pattern': Pattern,
        'MealPlan': MealPlan,
        'NutritionLog': NutritionLog,
        'DailyNutritionSummary': DailyNutritionSummary,
        'UserGoal': UserGoal,
        'UserFeedback': UserFeedback,
        'ChatSession': ChatSession,
        'ChatMessage': ChatMessage,
        'ChatSummary': ChatSummary,
        'MessageIntent': MessageIntent,
        'AIRecommendation': AIRecommendation,
    }


def _build_allowed_models_schema(models_map):
    schema = {}

    for model_key, model in models_map.items():
        fields = []

        for field in model._meta.fields:
            if getattr(field, 'auto_created', False) and not getattr(field, 'primary_key', False):
                continue

            field_info = {
                'name': field.name,
                'attname': getattr(field, 'attname', field.name),
                'type': field.get_internal_type(),
                'required': (
                    not getattr(field, 'blank', False)
                    and not getattr(field, 'null', False)
                    and not getattr(field, 'primary_key', False)
                ),
            }

            if getattr(field, 'many_to_one', False):
                field_info['relation'] = field.related_model.__name__

            fields.append(field_info)

        schema[model_key] = {
            'model_name': model.__name__,
            'fields': fields,
        }

    return schema


def _ask_qwen_import_classifier(headers, sample_rows, models_map):
    allowed_schema = _build_allowed_models_schema(models_map)
    prompt = f"""
Ban la module phan loai CSV cho he thong Smart Home Chef.

Nhiem vu:
1. Xac dinh file CSV phu hop voi model Django nao.
2. Map header CSV sang field cua model do.
3. Chi duoc dung model_key va field co trong allowed_models.
4. Khong duoc bia model moi.
5. Khong duoc bia field moi.
6. Neu header qua mo ho thi tra need_manual_confirm = true.
7. Chi tra ve JSON hop le, khong giai thich ngoai JSON.

Headers CSV:
{json.dumps(headers, ensure_ascii=False)}

Sample rows:
{json.dumps(sample_rows, ensure_ascii=False)}

Allowed models:
{json.dumps(allowed_schema, ensure_ascii=False)}

JSON bat buoc:
{{
  "target_model_key": "model_key hoac null",
  "confidence": 0.0,
  "need_manual_confirm": false,
  "header_mapping": {{
    "field_name": "CSV Header"
  }},
  "reason": "ly do ngan gon",
  "warnings": []
}}
"""

    try:
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat",
            json={
                'model': settings.OLLAMA_IMPORT_MODEL,
                'messages': [
                    {
                        'role': 'system',
                        'content': 'Ban la bo phan loai CSV. Chi tra ve JSON hop le.',
                    },
                    {
                        'role': 'user',
                        'content': prompt,
                    },
                ],
                'stream': False,
                'format': 'json',
            },
            timeout=getattr(settings, 'IMPORT_QWEN_TIMEOUT', 120),
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        raise RuntimeError('Qwen local bi timeout khi phan tich CSV') from exc
    except requests.ConnectionError as exc:
        raise RuntimeError(
            f'Khong ket noi duoc Ollama tai {getattr(settings, "OLLAMA_BASE_URL", "")}. '
            'Hay kiem tra Ollama da chay chua.'
        ) from exc
    except requests.HTTPError as exc:
        message = ''
        try:
            message = response.json().get('error') or response.text
        except Exception:
            message = getattr(response, 'text', '') or str(exc)
        raise RuntimeError(f'Ollama/Qwen tra ve loi HTTP: {message}') from exc
    except requests.RequestException as exc:
        raise RuntimeError(f'Khong goi duoc Qwen local: {exc}') from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError('Ollama tra ve JSON HTTP khong hop le') from exc

    content = ((data.get('message') or {}).get('content') or '').strip()
    if not content:
        raise RuntimeError('Qwen khong tra ve noi dung phan loai')

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        preview = content[:300]
        raise RuntimeError(f'Qwen tra JSON sai dinh dang: {preview}') from exc


def _validate_qwen_import_plan(plan, headers, models_map):
    target_model_key = plan.get('target_model_key')
    confidence = float(plan.get('confidence') or 0)
    need_manual_confirm = bool(plan.get('need_manual_confirm', False))
    header_mapping = plan.get('header_mapping') or {}

    if need_manual_confirm:
        return False, 'Qwen yeu cau admin xac nhan model thu cong'

    if not target_model_key:
        return False, 'Qwen khong xac dinh duoc model dich'

    if target_model_key not in models_map:
        return False, f'Model khong hop le: {target_model_key}'

    min_confidence = getattr(settings, 'IMPORT_QWEN_MIN_CONFIDENCE', 0.65)
    if confidence < min_confidence:
        return False, f'Do tin cay thap: {confidence}'

    if not isinstance(header_mapping, dict):
        return False, 'header_mapping khong hop le'

    model = models_map[target_model_key]
    valid_fields = set()
    for field in model._meta.fields:
        valid_fields.add(field.name)
        attname = getattr(field, 'attname', None)
        if attname:
            valid_fields.add(attname)

    for system_field, csv_header in header_mapping.items():
        if system_field not in valid_fields:
            return False, f'Qwen map vao field khong ton tai: {system_field}'
        if csv_header not in headers:
            return False, f'Qwen map vao header khong co trong CSV: {csv_header}'

    return True, 'Import plan hop le'


def _classify_import_model_with_qwen(headers, sample_rows, target_model_key=None):
    models_map = _get_all_models()

    if target_model_key:
        if target_model_key not in models_map:
            return {
                'ok': False,
                'error': f'Model dich khong hop le: {target_model_key}',
            }
        model = models_map[target_model_key]
        normalized_headers = {_clean_text_value(header).lower() for header in headers if _clean_text_value(header)}
        direct_columns = _get_import_column_names(model)
        if normalized_headers & direct_columns:
            return {
                'ok': True,
                'source': 'manual',
                'model_key': target_model_key,
                'model': model,
                'header_mapping': {},
                'confidence': 1.0,
                'warnings': [],
            }

        if not getattr(settings, 'LOCAL_LLM_IMPORT_ENABLED', False):
            return {
                'ok': True,
                'source': 'manual',
                'model_key': target_model_key,
                'model': model,
                'header_mapping': {},
                'confidence': 1.0,
                'warnings': [
                    'Da giu model admin chon, nhung Qwen local dang tat nen khong ho tro mapping header nang cao.',
                ],
            }

        try:
            plan = _ask_qwen_import_classifier(
                headers=headers,
                sample_rows=sample_rows,
                models_map={target_model_key: model},
            )
        except Exception as exc:
            return {
                'ok': False,
                'error': str(exc),
            }

        if plan.get('target_model_key') != target_model_key:
            return {
                'ok': False,
                'error': f'Qwen khong giu dung model admin da chon: {target_model_key}',
                'qwen_plan': plan,
            }

        is_valid, message = _validate_qwen_import_plan(
            plan=plan,
            headers=headers,
            models_map={target_model_key: model},
        )
        if not is_valid:
            return {
                'ok': False,
                'error': message,
                'qwen_plan': plan,
            }

        return {
            'ok': True,
            'source': 'manual_qwen_mapping',
            'model_key': target_model_key,
            'model': model,
            'header_mapping': plan.get('header_mapping') or {},
            'confidence': float(plan.get('confidence') or 0),
            'warnings': plan.get('warnings') or [],
            'reason': plan.get('reason', ''),
        }

    if not getattr(settings, 'LOCAL_LLM_IMPORT_ENABLED', False):
        return {
            'ok': False,
            'error': 'Qwen local chua duoc bat trong settings',
        }

    try:
        plan = _ask_qwen_import_classifier(
            headers=headers,
            sample_rows=sample_rows,
            models_map=models_map,
        )
    except Exception as exc:
        return {
            'ok': False,
            'error': str(exc),
        }

    is_valid, message = _validate_qwen_import_plan(
        plan=plan,
        headers=headers,
        models_map=models_map,
    )
    if not is_valid:
        return {
            'ok': False,
            'error': message,
            'qwen_plan': plan,
        }

    model_key = plan['target_model_key']
    return {
        'ok': True,
        'source': 'qwen_local',
        'model_key': model_key,
        'model': models_map[model_key],
        'header_mapping': plan.get('header_mapping') or {},
        'confidence': float(plan.get('confidence') or 0),
        'warnings': plan.get('warnings') or [],
        'reason': plan.get('reason', ''),
    }


def _get_model_fields(model):
    return [f.name for f in model._meta.get_fields() if not f.many_to_one or f.auto_created is False]


def _get_import_column_names(model):
    column_names = set()
    for field in model._meta.fields:
        if getattr(field, 'auto_created', False) and not field.concrete:
            continue
        column_names.add(field.name.lower())
        attname = getattr(field, 'attname', '')
        if attname and attname != field.name:
            column_names.add(attname.lower())
    return column_names


def _detect_model_from_headers(headers):
    headers_lower = [_clean_text_value(h).lower() for h in headers if _clean_text_value(h)]
    unique_headers = list(dict.fromkeys(headers_lower))
    generic_headers = {'id', 'name', 'title', 'created_at', 'updated_at'}

    if unique_headers and all(h in generic_headers for h in unique_headers):
        return None, 0.0, {
            'ambiguous': True,
            'candidates': [],
            'reason': 'generic_headers_only',
        }

    models_map = _get_all_models()
    candidates = []
    for model_name, model in models_map.items():
        allowed_columns = _get_import_column_names(model)
        matched_headers = [h for h in unique_headers if h in allowed_columns]
        matched_count = len(matched_headers)
        if matched_count == 0:
            continue

        header_coverage = matched_count / max(len(unique_headers), 1)
        model_coverage = matched_count / max(len(allowed_columns), 1)
        score = header_coverage + (model_coverage * 0.15)

        candidates.append({
            'model_name': model_name,
            'model': model,
            'score': score,
            'matched_count': matched_count,
            'matched_headers': matched_headers,
        })

    if not candidates:
        return None, 0.0, {'ambiguous': False, 'candidates': []}

    candidates.sort(
        key=lambda item: (
            -item['score'],
            -item['matched_count'],
            len(item['matched_headers']),
            item['model_name'],
        )
    )
    best = candidates[0]

    if best['matched_count'] < 2:
        return None, best['score'], {
            'ambiguous': True,
            'candidates': candidates[:5],
            'reason': 'too_few_columns',
        }

    ambiguous = False
    if len(candidates) > 1:
        second = candidates[1]
        score_gap = best['score'] - second['score']
        if score_gap < 0.02 and second['matched_count'] == best['matched_count']:
            ambiguous = True

    return (
        (best['model_name'], best['model']) if not ambiguous else None,
        best['score'],
        {
            'ambiguous': ambiguous,
            'candidates': candidates[:5],
        },
    )


def _import_csv_unified(uploaded_file, dry_run=False, target_model_key=None):
    report = {
        'detected_model': None,
        'detected_model_key': None,
        'classification_source': None,
        'classification_confidence': None,
        'header_mapping': {},
        'total_rows': 0,
        'ok_rows': 0,
        'created_rows': 0,
        'updated_rows': 0,
        'error_rows': 0,
        'warning_rows': 0,
        'dry_run': bool(dry_run),
        'details': [],
    }

    try:
        csv_text, _detected_encoding = _decode_uploaded_csv(uploaded_file)
    except ValueError as exc:
        report['details'].append({'row': '-', 'status': 'error', 'message': str(exc)})
        report['error_rows'] = 1
        return report

    dialect = _detect_csv_dialect(csv_text)
    reader = csv.DictReader(io.StringIO(csv_text), dialect=dialect)
    if not reader.fieldnames:
        report['details'].append({'row': '-', 'status': 'error', 'message': 'CSV khong co header.'})
        report['error_rows'] = 1
        return report

    rows = list(reader)
    headers = reader.fieldnames
    sample_rows = rows[:10]

    classification = _classify_import_model_with_qwen(
        headers=headers,
        sample_rows=sample_rows,
        target_model_key=target_model_key,
    )
    if not classification['ok']:
        report['error_rows'] = max(report.get('total_rows', 0), 1)
        report['details'].append({
            'row': '-',
            'status': 'error',
            'message': classification['error'],
        })
        if classification.get('qwen_plan'):
            report['details'].append({
                'row': '-',
                'status': 'warning',
                'message': f"Qwen plan: {classification['qwen_plan']}",
            })
        return report

    model_key = classification['model_key']
    model = classification['model']
    header_mapping = classification.get('header_mapping') or {}
    report['detected_model'] = model.__name__
    report['detected_model_key'] = model_key
    report['classification_source'] = classification.get('source')
    report['classification_confidence'] = classification.get('confidence')
    report['header_mapping'] = header_mapping

    if classification.get('reason'):
        report['details'].append({
            'row': '-',
            'status': 'warning',
            'message': f"Ly do phan loai: {classification['reason']}",
        })
    for warning in classification.get('warnings', []):
        report['details'].append({
            'row': '-',
            'status': 'warning',
            'message': str(warning),
        })

    pk_name = model._meta.pk.name

    for idx, raw_row in enumerate(rows, start=2):
        report['total_rows'] += 1
        payload, warnings, errors = _csv_row_to_model_payload(
            model=model,
            raw_row=raw_row,
            header_mapping=header_mapping,
        )
        pk_raw = raw_row.get(pk_name) or raw_row.get('id')
        pk_text = _clean_text_value(pk_raw)

        if warnings:
            report['warning_rows'] += 1

        if errors:
            report['error_rows'] += 1
            report['details'].append({
                'row': idx,
                'status': 'error',
                'message': '; '.join(errors),
            })
            continue

        instance = None
        if pk_text:
            instance = model.objects.filter(pk=pk_text).first()

        try:
            if instance:
                for key, value in payload.items():
                    setattr(instance, key, value)
                instance.full_clean()
                if not dry_run:
                    instance.save()
                report['updated_rows'] += 1
            else:
                instance = model(**payload)
                instance.full_clean()
                if not dry_run:
                    instance.save()
                report['created_rows'] += 1

            report['ok_rows'] += 1
            if warnings:
                report['details'].append({
                    'row': idx,
                    'status': 'warning',
                    'message': '; '.join(warnings),
                })
        except ValidationError as exc:
            report['error_rows'] += 1
            report['details'].append({
                'row': idx,
                'status': 'error',
                'message': '; '.join(exc.messages),
            })
        except Exception as exc:
            report['error_rows'] += 1
            report['details'].append({
                'row': idx,
                'status': 'error',
                'message': str(exc),
            })

    report['details'] = report['details'][:120]
    return report


def _import_csv_to_model(model, uploaded_file, dry_run=False):
    report = {
        'total_rows': 0,
        'ok_rows': 0,
        'created_rows': 0,
        'updated_rows': 0,
        'error_rows': 0,
        'warning_rows': 0,
        'dry_run': bool(dry_run),
        'details': [],
    }

    try:
        content = uploaded_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        content = uploaded_file.read().decode('latin-1')

    reader = csv.DictReader(content.splitlines())
    if not reader.fieldnames:
        report['details'].append({'row': '-', 'status': 'error', 'message': 'File CSV khong co header hop le.'})
        report['error_rows'] = 1
        return report

    pk_name = model._meta.pk.name

    for idx, raw_row in enumerate(reader, start=2):
        report['total_rows'] += 1
        payload, warnings, errors = _csv_row_to_model_payload(model, raw_row)
        pk_raw = raw_row.get(pk_name) or raw_row.get('id')
        pk_text = _clean_text_value(pk_raw)

        if warnings:
            report['warning_rows'] += 1

        if errors:
            report['error_rows'] += 1
            report['details'].append({
                'row': idx,
                'status': 'error',
                'message': '; '.join(errors),
            })
            continue

        instance = None
        if pk_text:
            instance = model.objects.filter(pk=pk_text).first()

        try:
            if instance:
                for key, value in payload.items():
                    setattr(instance, key, value)
                instance.full_clean()
                if not dry_run:
                    instance.save()
                report['updated_rows'] += 1
            else:
                instance = model(**payload)
                instance.full_clean()
                if not dry_run:
                    instance.save()
                report['created_rows'] += 1

            report['ok_rows'] += 1
            if warnings:
                report['details'].append({
                    'row': idx,
                    'status': 'warning',
                    'message': '; '.join(warnings),
                })
        except ValidationError as exc:
            report['error_rows'] += 1
            report['details'].append({
                'row': idx,
                'status': 'error',
                'message': '; '.join(exc.messages),
            })
        except Exception as exc:
            report['error_rows'] += 1
            report['details'].append({
                'row': idx,
                'status': 'error',
                'message': str(exc),
            })

    report['details'] = report['details'][:120]
    return report


def _admin_model_redirect(model_key, query_text='', page='', edit_pk=''):
    base_url = reverse('admin_model_manager', kwargs={'model_key': model_key})
    params = {}
    if query_text:
        params['q'] = query_text
    page_text = str(page).strip()
    if page_text and page_text != '1':
        params['page'] = page_text
    if edit_pk:
        params['edit'] = edit_pk
    query = urlencode(params)
    return f'{base_url}?{query}' if query else base_url


def _csv_report_session_key(model_key):
    return f'admin_csv_report_{model_key}'


def _pop_csv_report(request, model_key):
    session_key = _csv_report_session_key(model_key)
    return request.session.pop(session_key, None)
