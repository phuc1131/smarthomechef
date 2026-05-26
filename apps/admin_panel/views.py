import json
from datetime import date, timedelta
from urllib.parse import quote

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.forms import modelform_factory
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.users.models import Account, UserFeedback
from apps.nutrition.models import Food, NutritionLog, FoodIngredient
from apps.meal_plans.models import MealPlan
from apps.chat.models import ChatMessage, MessageIntent
from apps.users.auth_utils import verify_account_password
from apps.users.views import (
    _set_auth_session,
    is_admin_actor,
)
from .data_manager_service import (
    ADMIN_MODEL_LOOKUP,
    _admin_card_payload,
    _admin_csv_response,
    _dedupe_model_duplicates,
    _admin_model_redirect,
    _get_all_models,
    _get_selected_models,
    _group_summaries,
    _import_csv_to_model,
    _import_csv_unified,
    _list_preview_fields,
    _pop_csv_report,
    _safe_pk_value,
    _searchable_model_fields,
    _serialize_row,
)
from .crawl_control_service import (
    get_crawl_scheduler_status,
    start_crawl_scheduler,
    stop_crawl_scheduler,
)


def _redirect_admin_login(request):
    next_path = request.get_full_path()
    if next_path.startswith('/admin-panel/'):
        return redirect(f"/admin-panel/login/?next={quote(next_path, safe='/%?=&')}")
    return redirect('admin_login')


@require_GET
def admin_login_page(request):
    if is_admin_actor(request):
        return redirect('admin_data_manager')

    return render(request, 'admin_panel/login.html', {
        'next_url': (request.GET.get('next') or '').strip(),
    })


@require_POST
def admin_login_submit(request):
    username = (request.POST.get('username') or '').strip()
    password = (request.POST.get('password') or '').strip()
    next_url = (request.POST.get('next_url') or '').strip()

    if not username or not password:
        return render(request, 'admin_panel/login.html', {
            'error': 'Vui long nhap ten tai khoan va mat khau.',
            'next_url': next_url,
        })

    account = Account.objects.filter(username__iexact=username, is_active=True).first()
    if not account or not verify_account_password(account, password):
        return render(request, 'admin_panel/login.html', {
            'error': 'Ten tai khoan hoac mat khau khong dung.',
            'next_url': next_url,
        })

    role = (account.role or '').strip().lower()
    if role != 'admin':
        return render(request, 'admin_panel/login.html', {
            'error': 'Tai khoan nay khong co quyen admin.',
            'next_url': next_url,
        }, status=403)

    _set_auth_session(request, account.id, account.username, account.email)

    if next_url.startswith('/admin-panel/'):
        return redirect(next_url)
    return redirect('admin_data_manager')


def admin_model_manager(request, model_key):
    if not is_admin_actor(request):
        return _redirect_admin_login(request)

    if model_key not in ADMIN_MODEL_LOOKUP:
        return redirect('admin_data_manager')

    model_label, model = ADMIN_MODEL_LOOKUP[model_key]
    query_text = request.GET.get('q', '').strip()
    page = request.GET.get('page', '1').strip() or '1'
    edit_pk = request.GET.get('edit', '').strip()
    import_report = _pop_csv_report(request, model_key)

    pk_field_name = model._meta.pk.name
    preview_fields = _list_preview_fields(model)
    searchable_fields = _searchable_model_fields(model)
    list_qs = model.objects.all().order_by('-pk')

    if query_text:
        q_object = Q()
        for field_name in searchable_fields:
            q_object |= Q(**{f'{field_name}__icontains': query_text})
        if query_text.isdigit():
            q_object |= Q(pk=int(query_text))
        if q_object:
            list_qs = list_qs.filter(q_object)

    paginator = Paginator(list_qs, 12)
    page_obj = paginator.get_page(page)

    rows = []
    for obj in page_obj.object_list:
        data = _serialize_row(obj, preview_fields)
        rows.append({
            'pk': _safe_pk_value(getattr(obj, pk_field_name)),
            'data': data,
            'cells': [data.get(field_name, '') for field_name in preview_fields],
            'admin_change_url': f"/admin/app/{model._meta.model_name}/{getattr(obj, pk_field_name)}/change/",
        })

    FormClass = modelform_factory(model, fields='__all__')
    editing_instance = None
    if edit_pk:
        editing_instance = model.objects.filter(pk=edit_pk).first()

    form = FormClass(instance=editing_instance)

    if request.method == 'POST':
        action = (request.POST.get('action') or '').strip().lower()
        posted_query = (request.POST.get('q') or '').strip()
        posted_page = (request.POST.get('page') or '1').strip()
        posted_pk = (request.POST.get('pk') or '').strip()

        if action == 'delete':
            target = model.objects.filter(pk=posted_pk).first()
            if not target:
                messages.error(request, 'Khong tim thay ban ghi de xoa.')
            else:
                target.delete()
                messages.success(request, f'Da xoa ban ghi {posted_pk} cua {model_label}.')
            return redirect(_admin_model_redirect(model_key, posted_query, posted_page))

        if action == 'import_csv':
            csv_file = request.FILES.get('csv_file')
            dry_run = (request.POST.get('dry_run') or '').strip().lower() in {'1', 'true', 'on', 'yes'}

            if not csv_file:
                messages.error(request, 'Vui long chon file CSV truoc khi import.')
                return redirect(_admin_model_redirect(model_key, posted_query, posted_page, edit_pk))

            report = _import_csv_to_model(model, csv_file, dry_run=dry_run)
            request.session[f'admin_csv_report_{model_key}'] = report

            if report['error_rows'] == 0:
                if dry_run:
                    messages.success(request, f"Dry run thanh cong: {report['ok_rows']}/{report['total_rows']} dong hop le.")
                else:
                    messages.success(request, f"Import thanh cong: tao moi {report['created_rows']}, cap nhat {report['updated_rows']}.")
            else:
                summary = (
                    f"Import hoan tat voi loi: {report['error_rows']} dong loi, "
                    f"{report['ok_rows']} dong hop le."
                )
                messages.warning(request, summary)

            return redirect(_admin_model_redirect(model_key, posted_query, posted_page, edit_pk))

        if action == 'dedupe_duplicates':
            report = _dedupe_model_duplicates(model)
            if report['deleted_rows']:
                messages.success(
                    request,
                    f"Bot da xoa {report['deleted_rows']} ban ghi trung trong {model_label}. "
                    f"Da giu lai {report['kept_rows']} ban ghi.",
                )
            else:
                messages.info(request, f'Khong tim thay du lieu trung trong {model_label}.')
            return redirect(_admin_model_redirect(model_key, posted_query, posted_page, edit_pk))

        if action in {'create', 'update'}:
            instance = None
            if action == 'update':
                instance = model.objects.filter(pk=posted_pk).first()
                if not instance:
                    messages.error(request, 'Khong tim thay ban ghi de cap nhat.')
                    return redirect(_admin_model_redirect(model_key, posted_query, posted_page))

            form = FormClass(request.POST, instance=instance)
            if form.is_valid():
                saved_obj = form.save()
                msg = 'Da them moi ban ghi.' if action == 'create' else f'Da cap nhat ban ghi {saved_obj.pk}.'
                messages.success(request, msg)
                return redirect(_admin_model_redirect(model_key, posted_query, posted_page))

            messages.error(request, 'Du lieu khong hop le. Vui long kiem tra lai cac truong.')
            editing_instance = instance

    context = {
        'active': 'admin_model',
        'model_key': model_key,
        'model_label': model_label,
        'model_name': model._meta.model_name,
        'pk_field_name': pk_field_name,
        'query_text': query_text,
        'preview_fields': preview_fields,
        'rows': rows,
        'page_obj': page_obj,
        'form': form,
        'is_editing': bool(editing_instance),
        'editing_pk': _safe_pk_value(editing_instance.pk) if editing_instance else '',
        'total_count': list_qs.count(),
        'admin_model_url': f"/admin/app/{model._meta.model_name}/",
        'import_report': import_report,
    }
    return render(request, 'admin_panel/model_manager.html', context)


def admin_data_manager(request):
    if not is_admin_actor(request):
        return _redirect_admin_login(request)

    group_key = request.GET.get('group', 'all').strip().lower() or 'all'
    search_text = request.GET.get('q', '').strip()
    export_key = request.GET.get('export', '').strip()

    if export_key and export_key in ADMIN_MODEL_LOOKUP:
        label, model = ADMIN_MODEL_LOOKUP[export_key]
        return _admin_csv_response(label, model)

    selected_models = _get_selected_models(group_key, search_text)

    cards = []
    chart_labels = []
    chart_counts = []
    total_rows = 0
    total_recent_7d = 0

    for key, label, model in selected_models:
        card = _admin_card_payload(key, label, model)
        cards.append(card)
        chart_labels.append(label)
        chart_counts.append(card['count'])
        total_rows += card['count']
        total_recent_7d += card['recent_7d']

    cards.sort(key=lambda item: item['label'])
    group_summaries = _group_summaries(cards)

    day_labels = []
    chat_series = []
    meal_series = []
    nutrition_series = []
    for i in range(6, -1, -1):
        day_obj = date.today() - timedelta(days=i)
        day_str = day_obj.isoformat()
        day_labels.append(day_obj.strftime('%d/%m'))
        chat_series.append(ChatMessage.objects.filter(created_at__date=day_obj).count())
        meal_series.append(MealPlan.objects.filter(date__startswith=day_str).count())
        nutrition_series.append(NutritionLog.objects.filter(date=day_obj).count())

    intent_qs = (
        MessageIntent.objects
        .values('intent__name')
        .annotate(total=Count('id'))
        .order_by('-total')[:8]
    )
    intent_labels = [item['intent__name'] or 'unclassified' for item in intent_qs]
    intent_counts = [item['total'] for item in intent_qs]

    top_cards = sorted(cards, key=lambda item: item['count'], reverse=True)[:5]
    top_labels = [item['label'] for item in top_cards]
    top_counts = [item['count'] for item in top_cards]
    stats_table = sorted(cards, key=lambda item: item['count'], reverse=True)
    crawl_scheduler = get_crawl_scheduler_status()

    context = {
        'active': 'admin_data',
        'group_key': group_key,
        'search_text': search_text,
        'cards': cards,
        'total_models': len(cards),
        'total_rows': total_rows,
        'total_recent_7d': total_recent_7d,
        'group_summaries': group_summaries,
        'model_chart_labels': json.dumps(chart_labels, ensure_ascii=False),
        'model_chart_counts': json.dumps(chart_counts),
        'top_model_labels': json.dumps(top_labels, ensure_ascii=False),
        'top_model_counts': json.dumps(top_counts),
        'trend_labels': json.dumps(day_labels),
        'trend_chat': json.dumps(chat_series),
        'trend_meal': json.dumps(meal_series),
        'trend_nutrition': json.dumps(nutrition_series),
        'intent_labels': json.dumps(intent_labels, ensure_ascii=False),
        'intent_counts': json.dumps(intent_counts),
        'active_tab': group_key,
        'stats_table': stats_table,
        'crawl_scheduler': crawl_scheduler,
    }
    return render(request, 'admin_panel/data_manager.html', context)


@require_POST
def admin_crawl_control(request):
    if not is_admin_actor(request):
        return _redirect_admin_login(request)

    action = (request.POST.get('crawl_action') or '').strip().lower()

    if action == 'start':
        ok, message = start_crawl_scheduler()
        if ok:
            messages.success(request, message)
        else:
            messages.warning(request, message)
    elif action == 'stop':
        ok, message = stop_crawl_scheduler()
        if ok:
            messages.success(request, message)
        else:
            messages.warning(request, message)
    else:
        messages.error(request, 'Hanh dong crawl khong hop le.')

    return redirect('admin_data_manager')


@require_GET
def unified_import_csv(request):
    if not is_admin_actor(request):
        return _redirect_admin_login(request)

    report = None
    session_key = 'unified_csv_report'
    if session_key in request.session:
        report = request.session.pop(session_key)

    models_map = _get_all_models()
    context = {
        'active': 'admin_import',
        'models': [{'key': k, 'name': v.__name__} for k, v in models_map.items()],
        'report': report,
    }
    return render(request, 'admin_panel/unified_import.html', context)


@require_POST
def unified_import_csv_submit(request):
    if not is_admin_actor(request):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if 'csv_file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    uploaded_file = request.FILES['csv_file']
    dry_run = request.POST.get('dry_run') == 'on'
    target_model_key = (request.POST.get('target_model') or '').strip() or None

    report = _import_csv_unified(uploaded_file, dry_run=dry_run, target_model_key=target_model_key)
    request.session['unified_csv_report'] = report

    return redirect('unified_import_csv')


@require_GET
def admin_data_export(request, model_key):
    if not is_admin_actor(request):
        return _redirect_admin_login(request)

    if model_key not in ADMIN_MODEL_LOOKUP:
        return redirect('admin_data_manager')

    label, model = ADMIN_MODEL_LOOKUP[model_key]
    return _admin_csv_response(label, model)