from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.core.cache import cache
from common.responses import APIResponse
from common.permissions import IsAdminUser, IsTechnician
from .serializers import (
    TechnicianRegisterSerializer, TechnicianOnboardingSerializer,
    TechnicianProfileSerializer, TechnicianProfileUpdateSerializer
)
from rest_framework.permissions import AllowAny
from .services import TechnicianService
from django.shortcuts import get_object_or_404
from services.models import ServiceCategory
from .models import TechnicianProfile
from django.utils import timezone
from common.geocoding import geocode_address, haversine_km
from bookings.services import notify_all_admins, notify_all_technician_watchers
from notifications.services import NotificationService


class TechnicianRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = TechnicianRegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            result = TechnicianService.register_technician(serializer.validated_data)

            return APIResponse.success(
                data=result,
                message="Technician registered successfully. Please complete onboarding to get approved.",
                status=status.HTTP_201_CREATED,
            )
        except:
            return APIResponse.error(
                message="Registration failed. Please try again.",
                status=status.HTTP_400_BAD_REQUEST
            )


class TechnicianOnboardingView(APIView):
    permission_classes = [IsAuthenticated, IsTechnician]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            serializer = TechnicianOnboardingSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            profile = TechnicianService.submit_onboarding(request.user, serializer.validated_data)

            notify_all_admins("technician_onboarding", technician_id=profile.id)

            return APIResponse.success(
                data=TechnicianProfileSerializer(profile).data,
                message="Onboarding submitted successfully. Awaiting admin approval.",
                status=status.HTTP_200_OK,
            )
        except:
            return APIResponse.error(
                message="Onboarding submission failed. Please check your input and try again.",
                status=status.HTTP_400_BAD_REQUEST
            )


class TechnicianProfileView(APIView):
    permission_classes = [IsAuthenticated, IsTechnician]

    def get(self, request):
        try:
            profile = TechnicianService.get_profile(request.user)
            return APIResponse.success(
                data=TechnicianProfileSerializer(profile).data,
                message="Profile fetched successfully.",
                status=status.HTTP_200_OK,
            )
        except:
            return APIResponse.error(
                message="Failed to fetch profile.",
                status=status.HTTP_400_BAD_REQUEST
            )

    def patch(self, request):
        try:
            serializer = TechnicianProfileUpdateSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            profile = TechnicianService.update_profile(request.user, serializer.validated_data)
            
            message = "Profile updated."
            if profile.verification_status == "PENDING":
                message += " Re-approval required for changed KYC details."
                from django.contrib.auth import get_user_model
                User = get_user_model()
                for admin in User.objects.filter(role="ADMIN"):
                    NotificationService.create_notification(
                        admin.id,
                        "Technician Profile Edited",
                        f"{request.user.full_name or 'A technician'} updated their profile and requires re-approval.",
                    )
                notify_all_admins("technician_profile_edited", technician_id=profile.id)
                notify_all_technician_watchers("technician_profile_edited", technician_id=profile.id)
            
            return APIResponse.success(
                data=TechnicianProfileSerializer(profile).data,
                message=message,
                status=status.HTTP_200_OK,
            )
        except:
            return APIResponse.error(
                message="Profile update failed. Please try again.",
                status=status.HTTP_400_BAD_REQUEST
            )


def get_technicians_by_category_sorted(category_id, user_lat=None, user_lng=None):
    """
    Reusable core logic: fetch approved technicians for a category,
    optionally sorted by distance. Returns (data_list, error_message_or_None).
    """
    try:
        if not ServiceCategory.objects.filter(id=category_id).exists():
            return None, "Invalid category."

        if bool(user_lat) != bool(user_lng):
            return None, "user_lat and user_lng must be provided together."

        cache_key = f"technicians_by_category:{category_id}"
        data = cache.get(cache_key)

        if data is None:
            technicians = TechnicianProfile.objects.filter(
                specialization_id=category_id,
                verification_status="APPROVED",
            )
            data = TechnicianProfileSerializer(technicians, many=True).data
            cache.set(cache_key, data, timeout=600)

        if user_lat and user_lng:
            try:
                user_lat = float(user_lat)
                user_lng = float(user_lng)
            except (TypeError, ValueError):
                return None, "user_lat and user_lng must be valid numbers."

            for item in data:
                dist = haversine_km(
                    user_lat, user_lng,
                    float(item.get("latitude") or 0),
                    float(item.get("longitude") or 0),
                )
                item["distance_km"] = round(dist, 2) if item.get("latitude") else None

            data = sorted(data, key=lambda item: item["distance_km"] if item["distance_km"] is not None else float("inf"))

        return data, None
    except:
        return None, "An error occurred while fetching technicians."


class TechniciansByCategoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, category_id):
        try:
            user_lat = request.query_params.get("user_lat")
            user_lng = request.query_params.get("user_lng")

            data, error = get_technicians_by_category_sorted(category_id, user_lat, user_lng)
            if error:
                return APIResponse.error(message=error, status=400)

            return APIResponse.success(
                data=data,
                message="Technicians fetched successfully.",
                status=status.HTTP_200_OK,
            )
        except:
            return APIResponse.error(
                message="Failed to fetch technicians. Please try again.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )