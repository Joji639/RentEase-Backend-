from rest_framework.permissions import BasePermission


class HasCustom2FAPermission(BasePermission):
    message = "You do not have permission to manage two-factor authentication."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm("accounts.can_enable_2fa")
        )


class IsAdminUser(BasePermission):
    message = "This action is restricted to administrators only."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "ADMIN"
        )


class IsTechnician(BasePermission):
    message = "This action is restricted to technicians only."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "TECHNICIAN"
        )


class IsApprovedTechnician(BasePermission):
    message = "Your technician account is not yet approved. Please complete onboarding and wait for admin approval."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role == "TECHNICIAN"):
            return False

        profile = getattr(request.user, "technician_profile", None)
        return bool(profile and profile.verification_status == "APPROVED")