from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from accounts.models import RoleChoices
from common.exceptions import ValidationException, NotFoundException
from common.geocoding import geocode_address
from .models import TechnicianProfile, VerificationStatus

User = get_user_model()


def _geocode_if_needed(profile: TechnicianProfile, validated_data: dict):
    """Geocode the latest service-area/address text for map filtering."""
    addr = validated_data.get("service_area") or validated_data.get("address")
    if addr:
        coords = geocode_address(addr)
        if coords:
            profile.latitude, profile.longitude = coords


class TechnicianService:
    """Business logic for technician registration, onboarding, and admin review."""

    @staticmethod
    @transaction.atomic
    def register_technician(validated_data: dict) -> dict:
        from authentication.services import AuthService  # local import avoids circular dependency

        validated_data.pop("confirm_password")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            role=RoleChoices.TECHNICIAN,
            **validated_data,
        )

        TechnicianProfile.objects.create(user=user)

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
    def get_profile(user) -> TechnicianProfile:
        try:
            return user.technician_profile
        except TechnicianProfile.DoesNotExist:
            raise NotFoundException("Technician profile not found.")

    @staticmethod
    def submit_onboarding(user, validated_data: dict) -> TechnicianProfile:
        profile = TechnicianService.get_profile(user)

        if profile.verification_status == VerificationStatus.APPROVED:
            raise ValidationException("Your account is already approved. Cannot resubmit onboarding.")

        for field, value in validated_data.items():
            setattr(profile, field, value)

        if not profile.is_onboarding_complete():
            raise ValidationException("Please provide all required documents: license and PAN card.")

        _geocode_if_needed(profile, validated_data)
        profile.verification_status = VerificationStatus.PENDING
        profile.submitted_at = timezone.now()
        profile.rejection_reason = ""
        profile.save()

        return profile
    

    LOCKED_FIELDS = {"specialization", "license_number", "license_document", "pan_number", "pan_card_document", "certification_document"}
    @staticmethod
    def update_profile(user, validated_data: dict):
        profile = TechnicianProfile.objects.get(user=user)

        changed_locked = False
        for field in TechnicianService.LOCKED_FIELDS:
            if field in validated_data:
                new_value = validated_data[field]
                current_value = getattr(profile, field)
                if new_value != current_value:
                    changed_locked = True
                    break

        for field, value in validated_data.items():
            setattr(profile, field, value)

        _geocode_if_needed(profile, validated_data)

        if changed_locked:
            profile.verification_status = "PENDING"
            profile.reviewed_at = None
            profile.rejection_reason = ""   # ← changed from None to ""

        profile.save()
        return profile
