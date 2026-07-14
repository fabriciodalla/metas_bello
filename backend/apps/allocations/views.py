from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import GoalAllocation
from .serializers import DistributeRequestSerializer, GoalAllocationSerializer
from .services import (
    AllocationClosureError,
    AllocationReopenError,
    AllocationScopeError,
    ChildAllocationSpec,
    DistributeGoalService,
    ReopenAllocationService,
)


class GoalAllocationViewSet(ReadOnlyModelViewSet):
    serializer_class = GoalAllocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = GoalAllocation.objects.visible_to(self.request.user).select_related("owner_node")
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

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        allocation = self.get_object()

        try:
            ReopenAllocationService.reopen(allocation, criado_por=request.user)
        except (AllocationScopeError, AllocationReopenError) as exc:
            return Response({"detail": ", ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(GoalAllocationSerializer(allocation).data, status=status.HTTP_200_OK)
