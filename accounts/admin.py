# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailOTP

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_email_verified", "is_staff", "is_superuser")
    list_filter = ("role", "is_email_verified", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Extra", {"fields": ("role", "is_email_verified")}),
    )

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "code", "created_at", "expires_at", "used", "user")
    readonly_fields = ("created_at",)

