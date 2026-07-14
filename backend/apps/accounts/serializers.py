from rest_framework import serializers

from apps.hierarchy.models import HierarchyNode

from .models import User


class HierarchyNodeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = HierarchyNode
        fields = ["id", "level", "nome"]


class UserSerializer(serializers.ModelSerializer):
    hierarchy_nodes = HierarchyNodeSummarySerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "is_admin", "hierarchy_nodes"]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
