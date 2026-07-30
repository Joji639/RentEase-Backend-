from rest_framework import serializers
from services.models import ServiceCategory
from django.contrib.auth import get_user_model
User = get_user_model()





class AdminTechnicianRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False)


class AdminServiceCategoryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    icon = serializers.ImageField(required=False)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_name(self, value):
        value = value.strip()
        if ServiceCategory.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("A category with this name already exists.")
        return value


class AdminServiceCategoryUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    icon = serializers.ImageField(required=False)
    is_active = serializers.BooleanField(required=False)

    def validate_name(self, value):
        value = value.strip()
        qs = ServiceCategory.objects.filter(name__iexact=value)

        instance_id = self.context.get("category_id")
        if instance_id:
            qs = qs.exclude(id=instance_id)

        if qs.exists():
            raise serializers.ValidationError("A category with this name already exists.")
        return value
    


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "email", "phone_number", "is_active", "created_at"]
        read_only_fields = ["id", "email", "created_at"]

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "phone_number", "is_active"]





class AdminUserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    full_name = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

class AdminTechnicianCreateSerializer(AdminUserCreateSerializer):
    pass