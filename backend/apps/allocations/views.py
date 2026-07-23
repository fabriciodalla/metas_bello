from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.catalog.models import ProductGroup
from apps.cycles.models import Cycle
from apps.hierarchy.models import HierarchyNode

from .models import GoalAllocation
from .serializers import (
    ChildDistributionContextSerializer,
    CreateRootAllocationSerializer,
    DistributeRequestSerializer,
    GoalAllocationSerializer,
    GroupSuggestionSerializer,
    SplitSubgroupsRequestSerializer,
    SubgroupDistributionContextSerializer,
)
from .services import (
    AllocationClosureError,
    AllocationReopenError,
    AllocationScopeError,
    ChildAllocationSpec,
    CreateRootAllocationError,
    CreateRootAllocationService,
    DistributeGoalService,
    DistributionContextService,
    GoalSuggestionService,
    ReopenAllocationService,
    SplitGroupIntoSubgroupsService,
    SubgroupDistributionContextService,
    SubgroupSplitSpec,
)


class GoalAllocationViewSet(ReadOnlyModelViewSet):
    serializer_class = GoalAllocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            GoalAllocation.objects.visible_to(self.request.user)
            .select_related("owner_node", "group", "subgroup__group")
            .prefetch_related("owner_node__users")
        )
        cycle_id = self.request.query_params.get("cycle")
        if cycle_id:
            queryset = queryset.filter(cycle_id=cycle_id)
        return queryset.order_by("-created_at")

    @action(detail=True, methods=["post"])
    def distribute(self, request, pk=None):
        parent = self.get_object()

        request_serializer = DistributeRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        children = [
            ChildAllocationSpec(
                owner_node_id=child["owner_node_id"],
                quantity_kg=child["quantity_kg"],
                granularity=child["granularity"],
                group_id=child.get("group_id"),
                subgroup_id=child.get("subgroup_id"),
                product_id=child.get("product_id"),
            )
            for child in request_serializer.validated_data["children"]
        ]

        try:
            created = DistributeGoalService.distribute(parent, children, criado_por=request.user)
        except (AllocationClosureError, AllocationScopeError) as exc:
            return Response({"detail": ", ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(GoalAllocationSerializer(created, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="distribution-context")
    def distribution_context(self, request, pk=None):
        """Contexto histórico por filho direto (histórico 12 meses, comparativos, participação e,
        quando aplicável ao nível, sugestão AUTO já aprovada) — só apoia a decisão manual de quem
        está distribuindo, nunca substitui."""
        allocation = self.get_object()

        if not request.user.hierarchy_nodes.filter(id=allocation.owner_node_id).exists():
            return Response(
                {"detail": "Você não tem acesso a essa alocação."}, status=status.HTTP_403_FORBIDDEN
            )

        contexts = DistributionContextService.build(allocation)
        return Response(ChildDistributionContextSerializer(contexts, many=True).data)

    @action(detail=True, methods=["get"], url_path="subgroup-distribution-context")
    def subgroup_distribution_context(self, request, pk=None):
        """Tela "Distribuir Produtos": sugestão de quanto cada subgrupo do grupo recebe da meta
        GROUP recebida pelo Coordenador Local, pra pré-preencher a divisão em subgrupos."""
        allocation = self.get_object()

        if not request.user.hierarchy_nodes.filter(id=allocation.owner_node_id).exists():
            return Response(
                {"detail": "Você não tem acesso a essa alocação."}, status=status.HTTP_403_FORBIDDEN
            )

        contexts = SubgroupDistributionContextService.build(allocation)
        return Response(SubgroupDistributionContextSerializer(contexts, many=True).data)

    @action(detail=True, methods=["post"], url_path="split-subgroups")
    def split_subgroups(self, request, pk=None):
        """Tela "Distribuir Produtos": persiste a quebra da meta GROUP em metas SUBGROUP, ainda
        dona do mesmo nó Local — a distribuição pra Supervisor acontece depois, na tela "Meta
        Supervisor", como um `distribute()` normal sobre cada uma dessas alocações SUBGROUP."""
        parent = self.get_object()

        request_serializer = SplitSubgroupsRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        specs = [
            SubgroupSplitSpec(subgroup_id=item["subgroup_id"], quantity_kg=item["quantity_kg"])
            for item in request_serializer.validated_data["subgroups"]
        ]

        try:
            created = SplitGroupIntoSubgroupsService.split(parent, specs, criado_por=request.user)
        except (AllocationClosureError, AllocationScopeError) as exc:
            return Response({"detail": ", ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(GoalAllocationSerializer(created, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        allocation = self.get_object()

        try:
            ReopenAllocationService.reopen(allocation, criado_por=request.user)
        except (AllocationScopeError, AllocationReopenError) as exc:
            return Response({"detail": ", ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(GoalAllocationSerializer(allocation).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def suggestions(self, request):
        """P1: sugestão automática por grupo pro Gerente, com breakdown auditável — pré-preenche
        a criação da meta raiz, nunca a substitui (revisão humana sempre exigida)."""
        cycle_id = request.query_params.get("cycle")
        owner_node_id = request.query_params.get("owner_node")
        if not cycle_id or not owner_node_id:
            return Response(
                {"detail": "Parâmetros cycle e owner_node são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cycle = get_object_or_404(Cycle, id=cycle_id)
        owner_node = get_object_or_404(HierarchyNode, id=owner_node_id)

        if not request.user.hierarchy_nodes.filter(id=owner_node.id).exists():
            return Response({"detail": "Você não tem acesso a esse nó."}, status=status.HTTP_403_FORBIDDEN)

        suggestions_by_group = GoalSuggestionService.suggest_for_cycle(cycle)
        groups_by_id = {group.id: group for group in ProductGroup.objects.filter(ativo=True)}
        created_group_ids = set(
            GoalAllocation.objects.filter(
                cycle=cycle, owner_node=owner_node, parent_allocation__isnull=True
            ).values_list("group_id", flat=True)
        )

        payload = [
            {
                "group_id": group_id,
                "group_nome": groups_by_id[group_id].nome,
                "trend_kg": suggestion.trend_kg,
                "seasonal_index": suggestion.seasonal_index,
                "suggested_kg": suggestion.suggested_kg,
                "has_gap": suggestion.has_gap,
                "same_month_last_year_kg": suggestion.same_month_last_year_kg,
                "history": [
                    {"ano": point.ano, "mes": point.mes, "quantity_kg": point.quantity_kg}
                    for point in suggestion.history
                ],
                "already_created": group_id in created_group_ids,
            }
            for group_id, suggestion in suggestions_by_group.items()
            if group_id in groups_by_id
        ]

        return Response(GroupSuggestionSerializer(payload, many=True).data)

    @action(detail=False, methods=["post"], url_path="root", url_name="root")
    def create_root(self, request):
        """Cria a meta raiz do Gerente (nível topo, sem alocação-pai) — o passo que hoje só
        existia via Django Admin. O valor sugerido (P1) só pré-preenche no frontend; o que chega
        aqui já é a decisão final do usuário."""
        request_serializer = CreateRootAllocationSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data

        cycle = get_object_or_404(Cycle, id=data["cycle_id"])
        owner_node = get_object_or_404(HierarchyNode, id=data["owner_node_id"])

        try:
            allocation = CreateRootAllocationService.create(
                cycle=cycle,
                owner_node=owner_node,
                granularity=data["granularity"],
                quantity_kg=data["quantity_kg"],
                criado_por=request.user,
                group_id=data.get("group_id"),
                subgroup_id=data.get("subgroup_id"),
                product_id=data.get("product_id"),
            )
        except (AllocationScopeError, CreateRootAllocationError) as exc:
            return Response({"detail": ", ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(GoalAllocationSerializer(allocation).data, status=status.HTTP_201_CREATED)
