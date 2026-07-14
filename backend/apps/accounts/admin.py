from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

UserAdmin.fieldsets = UserAdmin.fieldsets + (("Metas Bello", {"fields": ("is_admin", "hierarchy_nodes")}),)
UserAdmin.filter_horizontal = UserAdmin.filter_horizontal + ("hierarchy_nodes",)

admin.site.register(User, UserAdmin)
