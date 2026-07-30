from rest_framework import serializers
from .models import ServiceCategory


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "description", "icon", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ServiceCategoryPublicSerializer(serializers.ModelSerializer):
    """Lighter serializer for public/user-facing listing — no timestamps needed."""
    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "description", "icon"]