from rest_framework import serializers

from .models import GoalAllocation


class GoalAllocationSerializer(serializers.ModelSerializer):
    owner_node_level = serializers.CharField(source="owner_node.level", read_only=True)
    owner_node_nome = serializers.CharField(source="owner_node.nome", read_only=True)

    class Meta:
        model = GoalAllocation
        fields = [
            "id",
            "cycle",
            "owner_node",
            "owner_node_level",
            "owner_node_nome",
            "parent_allocation",
            "granularity",
            "group",
            "subgroup",
            "product",
            "quantity_kg",
            "distributed",
            "criado_por",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ChildAllocationInputSerializer(serializers.Serializer):
    owner_node_id = serializers.IntegerField()
    quantity_kg = serializers.IntegerField(min_value=0)
    granularity = serializers.ChoiceField(choices=GoalAllocation.Granularity.choices)
    group_id = serializers.IntegerField(required=False, allow_null=True)
    subgroup_id = serializers.IntegerField(required=False, allow_null=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)


class DistributeRequestSerializer(serializers.Serializer):
    children = ChildAllocationInputSerializer(many=True)
