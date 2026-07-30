from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status

from common.responses import APIResponse

from .serializers import ServiceCategoryPublicSerializer
from .services import ServiceCategoryService


class PublicServiceCategoryListView(APIView):
    """Public — anyone (even unauthenticated) can browse active service categories."""
    permission_classes = [AllowAny]

    def get(self, request):
        categories = ServiceCategoryService.list_active_categories()
        return APIResponse.success(
            data=ServiceCategoryPublicSerializer(categories, many=True).data,
            message="Service categories fetched successfully.",
            status=status.HTTP_200_OK,
        )