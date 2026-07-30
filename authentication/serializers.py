from rest_framework import serializers
from django.contrib.auth import get_user_model
from common.validators import validate_strong_password, validate_full_name, validate_phone_number

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_strong_password]
    )
    confirm_password = serializers.CharField(write_only=True, required=True)
    full_name = serializers.CharField(validators=[validate_full_name])
    phone_number = serializers.CharField(
        required=False, allow_null=True, validators=[validate_phone_number]
    )

    class Meta:
        model = User
        fields = ["email", "full_name", "phone_number", "password", "confirm_password"]

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_number(self, value):
        if value and User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return value.lower().strip()
    


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.lower().strip()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_email(self, value):
        return value.lower().strip()
    

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(required=True, validators=[validate_strong_password])
    confirm_password = serializers.CharField(required=True)

    def validate_email(self, value):
        return value.lower().strip()

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_strong_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs
    

class Enable2FAVerifySerializer(serializers.Serializer):
    code = serializers.CharField(required=True, min_length=6, max_length=6)


class Disable2FASerializer(serializers.Serializer):
    password = serializers.CharField(required=True)


class LoginVerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_email(self, value):
        return value.lower().strip()