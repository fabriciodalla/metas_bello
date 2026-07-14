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


class AllocationOverviewSerializer(serializers.ModelSerializer):
    """Visão do Administrador: quem possui cada alocação do ciclo, não só o nó dono — usada para
    identificar quais usuários ainda não distribuíram (não é escopada por `visible_to`, é
    deliberadamente global; só é servida atrás de `IsAppAdmin`)."""

    owner_node_level = serializers.CharField(source="owner_node.level", read_only=True)
    owner_node_nome = serializers.CharField(source="owner_node.nome", read_only=True)
    owner_node_usernames = serializers.SerializerMethodField()
    criado_por_username = serializers.CharField(source="criado_por.username", read_only=True)

    class Meta:
        model = GoalAllocation
        fields = [
            "id",
            "cycle",
            "owner_node",
            "owner_node_level",
            "owner_node_nome",
            "owner_node_usernames",
            "parent_allocation",
            "granularity",
            "quantity_kg",
            "distributed",
            "criado_por_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_owner_node_usernames(self, obj) -> list[str]:
        return [user.username for user in obj.owner_node.users.all()]


class ChildAllocationInputSerializer(serializers.Serializer):
    owner_node_id = serializers.IntegerField()
    quantity_kg = serializers.IntegerField(min_value=0)
    granularity = serializers.ChoiceField(choices=GoalAllocation.Granularity.choices)
    group_id = serializers.IntegerField(required=False, allow_null=True)
    subgroup_id = serializers.IntegerField(required=False, allow_null=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)


class DistributeRequestSerializer(serializers.Serializer):
    children = ChildAllocationInputSerializer(many=True)
