import csv
import io

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.permissions import IsAppAdmin
from apps.allocations.models import GoalAllocation
from apps.allocations.serializers import AllocationOverviewSerializer
from apps.allocations.services import CycleCompletenessChecker

from .models import Cycle
from .serializers import CycleSerializer, StuckAllocationSerializer
from .services import CloseCycleService, CycleNotCompleteError

ADMIN_ONLY_ACTIONS = ("distribution_overview", "export")


class CycleViewSet(ReadOnlyModelViewSet):
    queryset = Cycle.objects.all().order_by("-ano", "-mes")
    serializer_class = CycleSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ADMIN_ONLY_ACTIONS:
            return [IsAuthenticated(), IsAppAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=["get"])
    def completeness(self, request, pk=None):
        cycle = self.get_object()
        stuck = CycleCompletenessChecker.stuck_allocations(cycle)
        return Response(
            {
                "complete": not stuck,
                "stuck_allocations": StuckAllocationSerializer(stuck, many=True).data,
            }
        )

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        cycle = self.get_object()
        try:
            CloseCycleService.close(cycle)
        except CycleNotCompleteError as exc:
            return Response({"detail": ", ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CycleSerializer(cycle).data)

    @action(detail=True, methods=["get"], url_path="distribution-overview")
    def distribution_overview(self, request, pk=None):
        """Visão completa do Administrador: toda alocação do ciclo, em qualquer nível, com quem
        é dono do nó — não passa por `visible_to` (é intencionalmente global)."""
        cycle = self.get_object()
        allocations = (
            GoalAllocation.objects.filter(cycle=cycle)
            .select_related("owner_node", "criado_por")
            .prefetch_related("owner_node__users")
            .order_by("owner_node__level", "owner_node__nome")
        )
        return Response(AllocationOverviewSerializer(allocations, many=True).data)

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """Baixa a árvore inteira de alocações do ciclo (todos os níveis) em CSV."""
        cycle = self.get_object()
        allocations = (
            GoalAllocation.objects.filter(cycle=cycle)
            .select_related(
                "owner_node", "parent_allocation__owner_node", "group", "subgroup", "product", "criado_por"
            )
            .order_by("owner_node__level", "owner_node__nome")
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "alocacao_id",
                "ciclo",
                "no_nivel",
                "no_nome",
                "alocacao_pai_id",
                "no_pai_nome",
                "granularidade",
                "grupo",
                "subgrupo",
                "produto",
                "quantidade_kg",
                "distribuido",
                "criado_por",
                "criado_em",
            ]
        )
        for allocation in allocations:
            writer.writerow(
                [
                    allocation.id,
                    f"{cycle.mes:02d}/{cycle.ano}",
                    allocation.owner_node.level,
                    allocation.owner_node.nome,
                    allocation.parent_allocation_id or "",
                    allocation.parent_allocation.owner_node.nome if allocation.parent_allocation_id else "",
                    allocation.granularity,
                    allocation.group.nome if allocation.group_id else "",
                    allocation.subgroup.nome if allocation.subgroup_id else "",
                    allocation.product.nome if allocation.product_id else "",
                    allocation.quantity_kg,
                    "sim" if allocation.distributed else "não",
                    allocation.criado_por.username,
                    allocation.created_at.isoformat(),
                ]
            )

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename=meta_{cycle.ano}_{cycle.mes:02d}.csv"
        return response
