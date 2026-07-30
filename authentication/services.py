from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from common.exceptions import AuthenticationFailedException,ValidationException
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from accounts.models import RoleChoices
from django.utils import timezone
from .tasks import send_password_reset_otp_email, send_password_changed_notification
from django.core.cache import cache
from common.utils import (
    generate_otp, generate_totp_secret, get_totp_uri,
    generate_qr_code_base64, verify_totp_code,
)



User = get_user_model()


def _otp_cache_key(email: str) -> str:
    return f"otp:reset:{email}"



class AuthService:

    @staticmethod
    def register_user(validated_data: dict) -> dict:
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")

        try:
            user = User.objects.create_user(password=password, **validated_data)
        except Exception as exc:
            raise ValidationException(str(exc))

        tokens = AuthService.generate_tokens(user)

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
            },
            "tokens": tokens,
        }

    @staticmethod
    def generate_tokens(user) -> dict:
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
    

    @staticmethod
    def login_user(validated_data: dict) -> dict:
        email = validated_data["email"]
        password = validated_data["password"]

        User = get_user_model()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailedException("User not registered.")

        if not user.check_password(password):
            raise AuthenticationFailedException("Password incorrect.")

        if not user.is_active:
            raise AuthenticationFailedException("This account has been deactivated.")

        if user.is_two_factor_enabled:
            return {
                "requires_2fa": True,
                "email": user.email,
            }

        tokens = AuthService.generate_tokens(user)
        return {
            "requires_2fa": False,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
            },
            "tokens": tokens,
    }

    @staticmethod
    def verify_google_token(token: str) -> dict:
        try:
            payload = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            raise AuthenticationFailedException("Invalid or expired Google token.")

        if payload.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise AuthenticationFailedException("Invalid token issuer.")

        if not payload.get("email_verified", False):
            raise AuthenticationFailedException("Google email is not verified.")

        return payload

    @staticmethod
    def google_login(id_token_str: str) -> dict:
        payload = AuthService.verify_google_token(id_token_str)

        email = payload["email"].lower().strip()
        full_name = payload.get("name", "")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": full_name,
                "role": RoleChoices.USER,
                "is_verified": True,
            },
        )

        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        else:
            if not user.is_active:
                raise AuthenticationFailedException("This account has been deactivated.")

        tokens = AuthService.generate_tokens(user)

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
            },
            "tokens": tokens,
            "created": created,
        }
    @staticmethod
    def forgot_password(email: str) -> None:
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return

        otp = generate_otp(length=settings.PASSWORD_RESET_OTP_LENGTH)
        cache_key = _otp_cache_key(email)

        cache.set(
            cache_key,
            {"otp": otp, "attempts": 0},
            timeout=settings.PASSWORD_RESET_OTP_EXPIRY_MINUTES * 60,
        )

        send_password_reset_otp_email.delay(user.email, otp, user.full_name)



    @staticmethod
    def _get_valid_otp_data(email: str, otp: str) -> dict:
        cache_key = _otp_cache_key(email)
        data = cache.get(cache_key)

        if data is None:
            raise ValidationException("OTP has expired or is invalid. Please request a new one.")

        if data["attempts"] >= settings.PASSWORD_RESET_OTP_MAX_ATTEMPTS:
            cache.delete(cache_key)
            raise ValidationException("Too many incorrect attempts. Please request a new OTP.")

        if data["otp"] != otp:
            data["attempts"] += 1
            ttl = cache.ttl(cache_key) or settings.PASSWORD_RESET_OTP_EXPIRY_MINUTES * 60
            cache.set(cache_key, data, timeout=ttl)
            raise ValidationException("Incorrect OTP.")

        return data

    @staticmethod
    def verify_otp(email: str, otp: str) -> None:
        AuthService._get_valid_otp_data(email, otp)

    @staticmethod
    def reset_password(email: str, otp: str, new_password: str) -> None:
        AuthService._get_valid_otp_data(email, otp)

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            raise ValidationException("Invalid OTP or email.")

        user.set_password(new_password)
        user.save(update_fields=["password"])
        cache.delete(_otp_cache_key(email))

        send_password_changed_notification.delay(user.email, user.full_name)
    @staticmethod
    def change_password(user, old_password: str, new_password: str) -> None:
        if not user.check_password(old_password):
            raise AuthenticationFailedException("Old password is incorrect.")

        if old_password == new_password:
            raise ValidationException("New password must be different from the old password.")

        user.set_password(new_password)
        user.save(update_fields=["password"])

        send_password_changed_notification.delay(user.email, user.full_name)


    @staticmethod
    def verify_login_otp(email: str, code: str) -> dict:
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            raise AuthenticationFailedException("Invalid email or code.")

        if not user.is_two_factor_enabled or not user.two_factor_secret:
            raise ValidationException("Two-factor authentication is not enabled for this account.")

        if not verify_totp_code(user.two_factor_secret, code):
            raise ValidationException("Invalid or expired authentication code.")

        tokens = AuthService.generate_tokens(user)
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
            },
            "tokens": tokens,
        }

    @staticmethod
    def setup_2fa(user) -> dict:
        secret = generate_totp_secret()
        user.two_factor_secret = secret
        user.save(update_fields=["two_factor_secret"])

        uri = get_totp_uri(secret, user.email)
        qr_base64 = generate_qr_code_base64(uri)

        return {
            "secret": secret,
            "otpauth_uri": uri,
            "qr_code_base64": qr_base64,
        }

    @staticmethod
    def enable_2fa(user, code: str) -> None:
        if not user.two_factor_secret:
            raise ValidationException("2FA setup has not been initiated. Call setup first.")

        if not verify_totp_code(user.two_factor_secret, code):
            raise ValidationException("Invalid authentication code.")

        user.is_two_factor_enabled = True
        user.save(update_fields=["is_two_factor_enabled"])

    @staticmethod
    def disable_2fa(user, password: str) -> None:
        if not user.check_password(password):
            raise AuthenticationFailedException("Incorrect password.")

        user.is_two_factor_enabled = False
        user.two_factor_secret = None
        user.save(update_fields=["is_two_factor_enabled", "two_factor_secret"])