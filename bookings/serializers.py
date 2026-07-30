from rest_framework import serializers
from .models import ServiceRequest, ServicePart


class ServiceRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    technician_name = serializers.CharField(source="technician.user.full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    technician_latitude = serializers.DecimalField(source="technician.latitude", max_digits=9, decimal_places=6, read_only=True)
    technician_longitude = serializers.DecimalField(source="technician.longitude", max_digits=9, decimal_places=6, read_only=True)

    class Meta:
        model = ServiceRequest
        fields = [
            "id", "user", "user_name", "technician", "technician_name",
            "category", "category_name", "full_name", "phone_number",
            "date", "address", "notes", "status", "created_at",
            "user_latitude", "user_longitude", "current_tech_latitude",
            "current_tech_longitude", "technician_latitude", "technician_longitude",
            "distance_km", "travel_cost", "service_charge", "total_amount",
            "otp_verified", "started_at", "work_started_at", "completed_at",
            "payment_method", "razorpay_order_id", "razorpay_payment_id","email"
        ]
        read_only_fields = ["id", "user", "status", "created_at"]


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(required=True, allow_blank=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=True, allow_blank=False)
    date = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ServiceRequest
        fields = ["technician", "category", "full_name", "email", "phone_number", "date", "address", "notes"]


class ServiceRequestStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ACCEPTED", "REJECTED", "CANCELLED", "IN_PROGRESS", "COMPLETED"])


class VerifyArrivalOtpSerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=6)


class PriceEstimateSerializer(serializers.Serializer):
    technician = serializers.UUIDField()
    user_latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    user_longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)


class PayServiceSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=["CASH", "ONLINE"], default="ONLINE")


class VerifyOtpSerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=6)


class ServicePartSerializer(serializers.ModelSerializer):
    added_by_name = serializers.CharField(source="added_by.full_name", read_only=True)

    class Meta:
        model = ServicePart
        fields = [
            "id", "service_request", "added_by", "added_by_name",
            "part_name", "description", "quantity", "unit_price",
            "total_price", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "service_request", "added_by", "total_price", "status", "created_at", "updated_at"]


class ServicePartApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
