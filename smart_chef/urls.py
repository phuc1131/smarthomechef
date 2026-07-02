"""Root URL routing for Smart Home Chef."""

from django.contrib import admin
from django.urls import include, path

from django.conf import settings
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.static import static
from apps.admin_panel import views as admin_views

urlpatterns = [
    path('', include('app.urls')),
    path('', include('apps.nutrition.urls')),
    path('admin-panel/', admin_views.admin_data_manager, name='admin_panel_home'),
    path('admin-panel/login/', admin_views.admin_login_page, name='admin_login'),
    path('admin-panel/login/submit/', admin_views.admin_login_submit, name='admin_login_submit'),
    path('admin-panel/import/', admin_views.unified_import_csv, name='unified_import_csv'),
    path('admin-panel/import/submit/', admin_views.unified_import_csv_submit, name='unified_import_csv_submit'),
    path('admin-panel/data-manager/', admin_views.admin_data_manager, name='admin_data_manager'),
    path('admin-panel/ai-quality/', admin_views.admin_ai_quality_dashboard, name='admin_ai_quality_dashboard'),
    path('admin-panel/data-manager/crawl-control/', admin_views.admin_crawl_control, name='admin_crawl_control'),
    path('admin-panel/data-manager/model/<str:model_key>/', admin_views.admin_model_manager, name='admin_model_manager'),
    path('admin-panel/data-manager/export/<str:model_key>/', admin_views.admin_data_export, name='admin_data_export'),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

