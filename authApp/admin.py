from django.contrib import admin
from .models import CustomUser
from django.contrib.auth.admin import UserAdmin

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('company',)}),  # Add company field to the admin form
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('company',)}),  # Add company field to the admin form
    )

admin.site.register(CustomUser, CustomUserAdmin)
