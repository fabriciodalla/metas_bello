from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.allocations.services import CycleCompletenessChecker

from .models import Cycle
from .serializers import CycleSerializer, StuckAllocationSerializer
from .services import CloseCycleService, CycleNotCompleteError


class CycleViewSet(ReadOnlyModelViewSet):
    queryset = Cycle.objects.all().order_by("-ano", "-mes")
    serializer_class = CycleSerializer
    permission_classes = [IsAuthenticated]

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
