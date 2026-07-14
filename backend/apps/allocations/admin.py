from django.contrib import admin

from .models import GoalAllocation


@admin.register(GoalAllocation)
class GoalAllocationAdmin(admin.ModelAdmin):
    list_display = ("cycle", "owner_node", "granularity", "quantity_kg", "distributed", "parent_allocation")
    list_filter = ("cycle", "granularity", "distributed")
    readonly_fields = ("created_at", "updated_at")
