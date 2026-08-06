from decimal import Decimal
from rest_framework import serializers
from django.contrib.auth import get_user_model
from common.validators import (
    validate_strong_password, validate_full_name, validate_phone_number,
    validate_document_file, validate_image_file,
)
from .models import TechnicianProfile
from services.serializers import ServiceCategoryPublicSerializer
from services.models import ServiceCategory



User = get_user_model()


class TechnicianRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    full_name = serializers.CharField(required=True, validators=[validate_full_name])
    phone_number = serializers.CharField(required=True, validators=[validate_phone_number])
    password = serializers.CharField(write_only=True, required=True, validators=[validate_strong_password])
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs


class TechnicianOnboardingSerializer(serializers.ModelSerializer):
    specialization = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        required=True,
    )
    experience_years = serializers.IntegerField(required=True, min_value=0)
    service_area = serializers.CharField(required=True, allow_blank=False)
    license_number = serializers.CharField(required=True, allow_blank=False)
    pan_number = serializers.CharField(required=True, allow_blank=False)

    profile_image = serializers.ImageField(required=False, validators=[validate_image_file])
    license_document = serializers.FileField(required=True, validators=[validate_document_file])
    pan_card_document = serializers.FileField(required=True, validators=[validate_document_file])
    certification_document = serializers.FileField(required=False, validators=[validate_document_file])
    hourly_rate = serializers.DecimalField(max_digits=8, decimal_places=2, required=True, min_value=Decimal("0"))
    address = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)

    class Meta:
        model = TechnicianProfile
        fields = [
            "specialization", "experience_years", "service_area", "hourly_rate",
            "profile_image", "license_number", "license_document",
            "pan_number", "pan_card_document", "certification_document",
            "address", "latitude", "longitude",
        ]

    def validate_license_number(self, value):
        return value.strip()

    def validate_pan_number(self, value):
        return value.strip().upper()


class TechnicianProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    is_two_factor_enabled = serializers.BooleanField(source="user.is_two_factor_enabled", read_only=True)
    specialization = ServiceCategoryPublicSerializer(read_only=True)
    specialization_id = serializers.PrimaryKeyRelatedField(
        source="specialization", queryset=ServiceCategory.objects.filter(is_active=True),
        write_only=True, required=False
    )

    class Meta:
        model = TechnicianProfile
        fields = [
            "id", "email", "full_name", "specialization", "specialization_id",
            "experience_years", "service_area", "hourly_rate",
            "profile_image", "license_number", "license_document",
            "pan_number", "pan_card_document", "certification_document",
            "verification_status", "rejection_reason", "submitted_at", "reviewed_at",
            "address", "latitude", "longitude", "is_two_factor_enabled",
         ]
        read_only_fields = [f for f in fields if f != "specialization_id"]


class TechnicianProfileUpdateSerializer(serializers.ModelSerializer):
    specialization = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.filter(is_active=True), required=False
    )
    profile_image = serializers.ImageField(required=False, validators=[validate_image_file])
    license_document = serializers.FileField(required=False, validators=[validate_document_file])
    pan_card_document = serializers.FileField(required=False, validators=[validate_document_file])
    certification_document = serializers.FileField(required=False, validators=[validate_document_file])

    class Meta:
        model = TechnicianProfile
        fields = [
            "specialization", "experience_years", "service_area", "hourly_rate",
            "profile_image", "license_number", "license_document",
            "pan_number", "pan_card_document", "certification_document",
            "address", "latitude", "longitude",
        ]

