from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import HierarchyNode
from .serializers import HierarchyNodeSerializer


class HierarchyNodeViewSet(ReadOnlyModelViewSet):
    serializer_class = HierarchyNodeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HierarchyNode.objects.visible_to(self.request.user).order_by("level", "nome")
