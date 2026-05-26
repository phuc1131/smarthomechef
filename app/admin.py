from django.contrib import admin


# ============================================================================
# DASHBOARD / SITE CUSTOMIZATION
# ============================================================================
# All models are registered in their respective app admin.py files using @admin.register()
# This file serves as the central configuration point for admin site customization

admin.site.site_header = "Smart Chef - Quản lý hệ thống"
admin.site.site_title = "Smart Chef Admin"
admin.site.index_title = "Trang chính"
