from rest_framework import serializers
from .models import CustomUser


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "email", "full_name", "phone_number", "role", "is_two_factor_enabled", "latest_location", "latest_latitude", "latest_longitude"]
        read_only_fields = ["id", "email", "role", "is_two_factor_enabled", "latest_latitude", "latest_longitude"]

    def validate_phone_number(self, value):
        if value:
            qs = CustomUser.objects.filter(phone_number=value).exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("This phone number is already in use.")
        return value