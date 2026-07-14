from rest_framework import serializers

from .models import Product, ProductGroup, ProductSubgroup


class ProductGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductGroup
        fields = ["id", "nome", "ativo"]


class ProductSubgroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSubgroup
        fields = ["id", "nome", "group", "ativo"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "nome", "subgroup", "ativo"]
