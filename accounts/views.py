from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.exceptions import ValidationError
from .serializers import ProfileSerializer
from common.responses import APIResponse
from common.geocoding import geocode_address


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            serializer = ProfileSerializer(request.user)
            return APIResponse.success(
                data=serializer.data,
                message="Profile fetched.",
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return APIResponse.error(
                message="Failed to fetch profile.",
                errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request):
        try:
            serializer = ProfileSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            if "latest_location" in request.data and request.data["latest_location"]:
                coords = geocode_address(request.data["latest_location"])
                if coords:
                    user.latest_latitude, user.latest_longitude = coords
                    user.save(update_fields=["latest_latitude", "latest_longitude"])
            serializer = ProfileSerializer(user)
            return APIResponse.success(
                data=serializer.data,
                message="Profile updated.",
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return APIResponse.error(
                message="Validation failed.",
                errors=e.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return APIResponse.error(
                message="Failed to update profile.",
                errors=str(e),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )