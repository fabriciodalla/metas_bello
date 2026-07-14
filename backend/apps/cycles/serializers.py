from rest_framework import serializers

from .models import Cycle


class CycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cycle
        fields = ["id", "ano", "mes", "status", "created_at", "closed_at"]
        read_only_fields = ["status", "created_at", "closed_at"]


class StuckAllocationSerializer(serializers.Serializer):
    allocation_id = serializers.IntegerField()
    owner_node_id = serializers.IntegerField()
    owner_node_level = serializers.CharField()
    quantity_kg = serializers.IntegerField()
