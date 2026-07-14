from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Product, ProductGroup, ProductSubgroup
from .serializers import ProductGroupSerializer, ProductSerializer, ProductSubgroupSerializer


class ProductGroupViewSet(ReadOnlyModelViewSet):
    queryset = ProductGroup.objects.filter(ativo=True).order_by("nome")
    serializer_class = ProductGroupSerializer
    permission_classes = [IsAuthenticated]


class ProductSubgroupViewSet(ReadOnlyModelViewSet):
    serializer_class = ProductSubgroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ProductSubgroup.objects.filter(ativo=True).order_by("nome")
        group_id = self.request.query_params.get("group")
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        return queryset


class ProductViewSet(ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Product.objects.filter(ativo=True).order_by("nome")
        subgroup_id = self.request.query_params.get("subgroup")
        if subgroup_id:
            queryset = queryset.filter(subgroup_id=subgroup_id)
        return queryset
