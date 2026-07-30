from django.utils import timezone
from common.exceptions import ValidationException, NotFoundException
from technicians.models import TechnicianProfile, VerificationStatus
from django.contrib.auth import get_user_model
User = get_user_model()

class AdminTechnicianService:
    """Admin-side business logic for reviewing technician approvals."""

    @staticmethod
    def list_pending_technicians():
        return TechnicianProfile.objects.filter(
            verification_status=VerificationStatus.PENDING
        ).select_related("user").order_by("submitted_at")

    @staticmethod
    def approve_technician(admin_user, technician_profile_id) -> TechnicianProfile:
        try:
            profile = TechnicianProfile.objects.get(id=technician_profile_id)
        except TechnicianProfile.DoesNotExist:
            raise NotFoundException("Technician profile not found.")

        if profile.verification_status != VerificationStatus.PENDING:
            raise ValidationException("Only technicians with PENDING status can be approved.")

        profile.verification_status = VerificationStatus.APPROVED
        profile.reviewed_at = timezone.now()
        profile.reviewed_by = admin_user
        profile.rejection_reason = ""
        profile.save()

        profile.user.is_verified = True
        profile.user.save(update_fields=["is_verified"])

        return profile

    @staticmethod
    def reject_technician(admin_user, technician_profile_id, reason: str) -> TechnicianProfile:
        try:
            profile = TechnicianProfile.objects.get(id=technician_profile_id)
        except TechnicianProfile.DoesNotExist:
            raise NotFoundException("Technician profile not found.")

        if profile.verification_status != VerificationStatus.PENDING:
            raise ValidationException("Only technicians with PENDING status can be rejected.")

        profile.verification_status = VerificationStatus.REJECTED
        profile.reviewed_at = timezone.now()
        profile.reviewed_by = admin_user
        profile.rejection_reason = reason
        profile.save()

        return profile
    @staticmethod
    def list_all_technicians():
        return TechnicianProfile.objects.filter(
            verification_status=VerificationStatus.APPROVED
        ).order_by("-created_at")

    @staticmethod
    def delete_technician(technician_profile_id):
        try:
            profile = TechnicianProfile.objects.get(id=technician_profile_id)
        except TechnicianProfile.DoesNotExist:
            raise NotFoundException("Technician profile not found.")
        # delete associated user which should cascade to profile if configured
        profile.user.delete()

    @staticmethod
    def update_technician(technician_profile_id, validated_data):
        try:
            profile = TechnicianProfile.objects.get(id=technician_profile_id)
        except TechnicianProfile.DoesNotExist:
            raise NotFoundException("Technician profile not found.")
        for field, value in validated_data.items():
            setattr(profile, field, value)
        profile.save()
        return profile
    

    @staticmethod
    def create_technician(validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, role="TECHNICIAN", is_verified=True, **validated_data)
        TechnicianProfile.objects.create(user=user)
        return user
    




class AdminUserService:
    @staticmethod
    def list_users():
        return User.objects.filter(role="USER").order_by("-created_at")

    @staticmethod
    def update_user(user_id, validated_data):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFoundException("User not found.")
        for field, value in validated_data.items():
            setattr(user, field, value)
        user.save()
        return user

    @staticmethod
    def delete_user(user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFoundException("User not found.")
        user.delete()


    @staticmethod
    def create_user(validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, role="USER", is_verified=True, **validated_data)



    