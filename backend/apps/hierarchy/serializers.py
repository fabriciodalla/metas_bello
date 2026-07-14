from rest_framework import serializers

from .models import HierarchyNode


class HierarchyNodeSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = HierarchyNode
        fields = ["id", "level", "level_display", "parent", "nome", "ativo"]
