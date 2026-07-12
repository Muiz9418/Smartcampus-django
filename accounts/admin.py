from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Academic Info", {"fields": ("role", "matric_number", "department", "is_verified")}),
    )
    list_display = ("username", "email", "role", "is_verified", "is_staff")


admin.site.register(User, CustomUserAdmin)
