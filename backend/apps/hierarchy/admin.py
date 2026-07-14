from django.contrib import admin

from .models import ExternalSalespersonMapping, HierarchyClosure, HierarchyNode


@admin.register(HierarchyNode)
class HierarchyNodeAdmin(admin.ModelAdmin):
    list_display = ("nome", "level", "parent", "ativo")
    list_filter = ("level", "ativo")
    search_fields = ("nome",)

    def save_model(self, request, obj, form, change):
        previous = HierarchyNode.objects.filter(pk=obj.pk).first() if change else None
        super().save_model(request, obj, form, change)

        was_deactivated = previous is not None and previous.ativo and not obj.ativo
        was_reparented = previous is not None and previous.parent_id != obj.parent_id
        if was_deactivated or was_reparented:
            # Import tardio: allocations importa hierarchy.models, evita ciclo com hierarchy.admin.
            from apps.allocations.services import HierarchyChangeReassignmentService

            HierarchyChangeReassignmentService.reassign_open_cycle_allocations(obj, changed_by=request.user)


@admin.register(HierarchyClosure)
class HierarchyClosureAdmin(admin.ModelAdmin):
    list_display = ("ancestor", "descendant", "depth")
    list_filter = ("depth",)


@admin.register(ExternalSalespersonMapping)
class ExternalSalespersonMappingAdmin(admin.ModelAdmin):
    list_display = ("external_name", "hierarchy_node")
    search_fields = ("external_name", "hierarchy_node__nome")
