"""
core/admin.py — Register all models with the Django admin site.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ClaimEstimate, DamageInsight, User, VehicleImage


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "name", "is_staff", "created_at"]
    list_filter = ["is_staff", "is_active"]
    search_fields = ["email", "name", "google_uid"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name", "avatar_url", "google_uid")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("created_at", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2"),
        }),
    )
    readonly_fields = ["created_at"]


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "uploaded_at"]
    list_filter = ["status"]
    search_fields = ["user__email"]
    raw_id_fields = ["user"]


@admin.register(DamageInsight)
class DamageInsightAdmin(admin.ModelAdmin):
    list_display = ["id", "vehicle_image", "detected_part", "damage_type", "severity", "confidence", "created_at"]
    list_filter = ["severity"]
    search_fields = ["detected_part", "damage_type"]


@admin.register(ClaimEstimate)
class ClaimEstimateAdmin(admin.ModelAdmin):
    list_display = ["id", "damage_insight", "estimated_cost", "currency", "created_at"]
    search_fields = ["damage_insight__detected_part"]
