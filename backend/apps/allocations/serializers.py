from rest_framework import serializers

from .models import GoalAllocation


class GoalAllocationSerializer(serializers.ModelSerializer):
    owner_node_level = serializers.CharField(source="owner_node.level", read_only=True)
    owner_node_nome = serializers.CharField(source="owner_node.nome", read_only=True)
    owner_node_usernames = serializers.SerializerMethodField()
    group_nome = serializers.SerializerMethodField()
    subgroup_nome = serializers.SerializerMethodField()

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
            "group",
            "group_nome",
            "subgroup",
            "subgroup_nome",
            "product",
            "quantity_kg",
            "distributed",
            "criado_por",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_owner_node_usernames(self, obj) -> list[str]:
        return [user.username for user in obj.owner_node.users.all()]

    def get_group_nome(self, obj) -> str | None:
        if obj.group_id:
            return obj.group.nome
        if obj.subgroup_id:
            return obj.subgroup.group.nome
        return None

    def get_subgroup_nome(self, obj) -> str | None:
        return obj.subgroup.nome if obj.subgroup_id else None


class AllocationOverviewSerializer(serializers.ModelSerializer):
    """Visão do Administrador: quem possui cada alocação do ciclo, não só o nó dono — usada para
    identificar quais usuários ainda não distribuíram (não é escopada por `visible_to`, é
    deliberadamente global; só é servida atrás de `IsAppAdmin`)."""

    owner_node_level = serializers.CharField(source="owner_node.level", read_only=True)
    owner_node_nome = serializers.CharField(source="owner_node.nome", read_only=True)
    owner_node_parent_id = serializers.IntegerField(source="owner_node.parent_id", read_only=True)
    owner_node_parent_nome = serializers.SerializerMethodField()
    owner_node_usernames = serializers.SerializerMethodField()
    criado_por_username = serializers.CharField(source="criado_por.username", read_only=True)
    group_nome = serializers.SerializerMethodField()
    subgroup_nome = serializers.SerializerMethodField()

    class Meta:
        model = GoalAllocation
        fields = [
            "id",
            "cycle",
            "owner_node",
            "owner_node_level",
            "owner_node_nome",
            "owner_node_parent_id",
            "owner_node_parent_nome",
            "owner_node_usernames",
            "parent_allocation",
            "granularity",
            "group_nome",
            "subgroup_nome",
            "quantity_kg",
            "distributed",
            "criado_por_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_owner_node_usernames(self, obj) -> list[str]:
        return [user.username for user in obj.owner_node.users.all()]

    def get_owner_node_parent_nome(self, obj) -> str | None:
        return obj.owner_node.parent.nome if obj.owner_node.parent_id else None

    def get_group_nome(self, obj) -> str | None:
        if obj.group_id:
            return obj.group.nome
        if obj.subgroup_id:
            return obj.subgroup.group.nome
        return None

    def get_subgroup_nome(self, obj) -> str | None:
        return obj.subgroup.nome if obj.subgroup_id else None


class ChildAllocationInputSerializer(serializers.Serializer):
    owner_node_id = serializers.IntegerField()
    quantity_kg = serializers.IntegerField(min_value=0)
    granularity = serializers.ChoiceField(choices=GoalAllocation.Granularity.choices)
    group_id = serializers.IntegerField(required=False, allow_null=True)
    subgroup_id = serializers.IntegerField(required=False, allow_null=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)


class DistributeRequestSerializer(serializers.Serializer):
    children = ChildAllocationInputSerializer(many=True)


class MonthlyPointSerializer(serializers.Serializer):
    ano = serializers.IntegerField()
    mes = serializers.IntegerField()
    quantity_kg = serializers.FloatField()


class GroupSuggestionSerializer(serializers.Serializer):
    """P1 — sugestão por grupo com o breakdown auditável (Decisão 6)."""

    group_id = serializers.IntegerField()
    group_nome = serializers.CharField()
    trend_kg = serializers.IntegerField()
    seasonal_index = serializers.FloatField()
    suggested_kg = serializers.IntegerField()
    has_gap = serializers.BooleanField()
    same_month_last_year_kg = serializers.FloatField(allow_null=True)
    history = MonthlyPointSerializer(many=True)
    already_created = serializers.BooleanField()


class ChildDistributionContextSerializer(serializers.Serializer):
    """Contexto histórico por alvo direto, exibido na tela de distribuição (Gerente→Regional,
    Regional→Local) — nunca substitui a decisão manual, só informa."""

    owner_node_id = serializers.IntegerField()
    history = MonthlyPointSerializer(many=True)
    same_month_last_year_kg = serializers.FloatField(allow_null=True)
    last_3_months_avg_kg = serializers.FloatField(allow_null=True)
    historical_share_pct = serializers.FloatField(allow_null=True)
    has_gap = serializers.BooleanField()
    suggested_kg = serializers.IntegerField(allow_null=True)


class SubgroupDistributionContextSerializer(serializers.Serializer):
    """Contexto histórico por subgrupo, exibido na tela "Distribuir Produtos" (grupo→subgrupo do
    Coordenador Local) — mesma forma de `ChildDistributionContextSerializer`, chaveada por
    subgrupo em vez de nó."""

    subgroup_id = serializers.IntegerField()
    subgroup_nome = serializers.CharField()
    history = MonthlyPointSerializer(many=True)
    same_month_last_year_kg = serializers.FloatField(allow_null=True)
    last_3_months_avg_kg = serializers.FloatField(allow_null=True)
    historical_share_pct = serializers.FloatField(allow_null=True)
    has_gap = serializers.BooleanField()
    suggested_kg = serializers.IntegerField(allow_null=True)


class SubgroupSplitInputSerializer(serializers.Serializer):
    subgroup_id = serializers.IntegerField()
    quantity_kg = serializers.IntegerField(min_value=0)


class SplitSubgroupsRequestSerializer(serializers.Serializer):
    """Corpo de `POST /allocations/{id}/split-subgroups/` — tela "Distribuir Produtos"."""

    subgroups = SubgroupSplitInputSerializer(many=True)


class CreateRootAllocationSerializer(serializers.Serializer):
    cycle_id = serializers.IntegerField()
    owner_node_id = serializers.IntegerField()
    granularity = serializers.ChoiceField(choices=GoalAllocation.Granularity.choices)
    quantity_kg = serializers.IntegerField(min_value=0)
    group_id = serializers.IntegerField(required=False, allow_null=True)
    subgroup_id = serializers.IntegerField(required=False, allow_null=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)
