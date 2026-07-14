from django.contrib import admin

from .models import Cycle


@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = ("mes", "ano", "status", "created_at", "closed_at")
    list_filter = ("status", "ano")
