from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from common.responses import APIResponse
from common.permissions import IsAdminUser
from technicians.serializers import TechnicianProfileSerializer

from .serializers import AdminTechnicianRejectSerializer
from bookings.services import notify_user, notify_all_admins, notify_all_technician_watchers
from notifications.services import NotificationService, send_push_notification
from .services import AdminTechnicianService
from rest_framework.parsers import MultiPartParser, FormParser
from services.models import ServiceCategory
from services.serializers import ServiceCategorySerializer
from services.services import ServiceCategoryService
from .serializers import AdminServiceCategoryCreateSerializer, AdminServiceCategoryUpdateSerializer
from technicians.serializers import TechnicianProfileUpdateSerializer
from .serializers import AdminUserSerializer, AdminUserUpdateSerializer,AdminUserCreateSerializer, AdminTechnicianCreateSerializer
from .services import AdminUserService
from technicians.models import TechnicianProfile
from listings.models import ListingCategory,Listing
from listings.serializers import ListingCategorySerializer,ListingSerializer


class AdminPendingTechniciansView(APIView):
    """Admin — list all technicians awaiting approval."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        profiles = AdminTechnicianService.list_pending_technicians()
        return APIResponse.success(
            data=TechnicianProfileSerializer(profiles, many=True).data,
            message="Pending technicians fetched successfully.",
            status=status.HTTP_200_OK,
        )


class AdminApproveTechnicianView(APIView):
    """Admin — approve a pending technician."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, technician_id):
        profile = AdminTechnicianService.approve_technician(request.user, technician_id)
        notify_user(profile.user.id, "approved", technician_id=technician_id)
        notify_all_admins("technician_approved", technician_id=technician_id)
        notify_all_technician_watchers("technician_approved", technician_id=technician_id, category_id=str(profile.specialization_id) if profile.specialization_id else None)
        NotificationService.create_notification(
            profile.user.id,
            "Profile Approved",
            "Your technician profile has been approved by the admin.",
        )
        send_push_notification.delay(profile.user.id, "Profile Approved", "Your technician profile has been approved.")
        return APIResponse.success(
            data=TechnicianProfileSerializer(profile).data,
            message="Technician approved successfully.",
            status=status.HTTP_200_OK,
        )


class AdminRejectTechnicianView(APIView):
    """Admin — reject a pending technician with a reason."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, technician_id):
        serializer = AdminTechnicianRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = AdminTechnicianService.reject_technician(
            request.user, technician_id, serializer.validated_data["reason"]
        )
        notify_user(profile.user.id, "rejected", technician_id=technician_id, reason=serializer.validated_data["reason"])
        notify_all_admins("technician_rejected", technician_id=technician_id)
        notify_all_technician_watchers("technician_rejected", technician_id=technician_id, category_id=str(profile.specialization_id) if profile.specialization_id else None)
        NotificationService.create_notification(
            profile.user.id,
            "Profile Rejected",
            f"Your technician profile was rejected. Reason: {serializer.validated_data['reason']}",
        )
        send_push_notification.delay(profile.user.id, "Profile Rejected", f"Reason: {serializer.validated_data['reason']}")
        return APIResponse.success(
            data=TechnicianProfileSerializer(profile).data,
            message="Technician rejected.",
            status=status.HTTP_200_OK,
        )
    


class AdminServiceCategoryListCreateView(APIView):
    """Admin — list ALL categories (active + inactive) and create new ones."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        categories = ServiceCategoryService.list_all_categories()
        return APIResponse.success(
            data=ServiceCategorySerializer(categories, many=True).data,
            message="All service categories fetched successfully.",
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = AdminServiceCategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category = ServiceCategoryService.create_category(serializer.validated_data)

        return APIResponse.success(
            data=ServiceCategorySerializer(category).data,
            message="Service category created successfully.",
            status=status.HTTP_201_CREATED,
        )


class AdminServiceCategoryDetailView(APIView):
    """Admin — update or delete a specific category."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, category_id):
        serializer = AdminServiceCategoryUpdateSerializer(
            data=request.data, partial=True, context={"category_id": category_id}
        )
        serializer.is_valid(raise_exception=True)

        category = ServiceCategoryService.update_category(category_id, serializer.validated_data)

        return APIResponse.success(
            data=ServiceCategorySerializer(category).data,
            message="Service category updated successfully.",
            status=status.HTTP_200_OK,
        )

    def delete(self, request, category_id):
        ServiceCategoryService.delete_category(category_id)
        return APIResponse.success(message="Service category deleted successfully.", status=status.HTTP_200_OK)

class AdminServiceCategoryToggleActiveView(APIView):
    """Admin — quickly enable/disable a category without a full update."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, category_id):
        category = ServiceCategoryService.toggle_active(category_id)
        return APIResponse.success(
            data=ServiceCategorySerializer(category).data,
            message=f"Service category is now {'active' if category.is_active else 'inactive'}.",
            status=status.HTTP_200_OK,
        )
    


class AdminAllTechniciansView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    def get(self, request):
        profiles = AdminTechnicianService.list_all_technicians()
        return APIResponse.success(data=TechnicianProfileSerializer(profiles, many=True).data, message="Technicians fetched.", status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = AdminTechnicianCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminTechnicianService.create_technician(serializer.validated_data)
        profile = TechnicianProfile.objects.get(user=user)
        return APIResponse.success(data=TechnicianProfileSerializer(profile).data, message="Technician created.", status=status.HTTP_201_CREATED)

class AdminTechnicianDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    def patch(self, request, technician_id):
        serializer = TechnicianProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = AdminTechnicianService.update_technician(technician_id, serializer.validated_data)
        return APIResponse.success(data=TechnicianProfileSerializer(profile).data, message="Technician updated.", status=status.HTTP_200_OK)
    def delete(self, request, technician_id):
        AdminTechnicianService.delete_technician(technician_id)
        return APIResponse.success(message="Technician deleted.", status=status.HTTP_200_OK)
    



class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    def get(self, request):
        users = AdminUserService.list_users()
        return APIResponse.success(data=AdminUserSerializer(users, many=True).data, message="Users fetched.", status=status.HTTP_200_OK)
    

    def post(self, request):
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.create_user(serializer.validated_data)
        return APIResponse.success(data=AdminUserSerializer(user).data, message="User created.", status=status.HTTP_201_CREATED)


class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    def patch(self, request, user_id):
        serializer = AdminUserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.update_user(user_id, serializer.validated_data)
        return APIResponse.success(data=AdminUserSerializer(user).data, message="User updated.", status=status.HTTP_200_OK)
    def delete(self, request, user_id):
        AdminUserService.delete_user(user_id)
        return APIResponse.success(message="User deleted.", status=status.HTTP_200_OK)
    

class AdminListingCategoryListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        categories = ListingCategory.objects.all().order_by("name")
        return APIResponse.success(data=ListingCategorySerializer(categories, many=True).data, message="Categories fetched.", status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ListingCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return APIResponse.success(data=ListingCategorySerializer(category).data, message="Category created.", status=status.HTTP_201_CREATED)

class AdminListingCategoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, category_id):
        try:
            category = ListingCategory.objects.get(id=category_id)
        except ListingCategory.DoesNotExist:
            return APIResponse.error(message="Category not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = ListingCategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return APIResponse.success(data=ListingCategorySerializer(category).data, message="Category updated.", status=status.HTTP_200_OK)

    def delete(self, request, category_id):
        ListingCategory.objects.filter(id=category_id).delete()
        return APIResponse.success(message="Category deleted.", status=status.HTTP_200_OK)
    


class AdminListingListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        listings = Listing.objects.all().order_by("-created_at")
        return APIResponse.success(
            data=ListingSerializer(listings, many=True, context={"request": request}).data,
            message="Listings fetched.", status=status.HTTP_200_OK,
        )

class AdminListingDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, listing_id):
        deleted, _ = Listing.objects.filter(id=listing_id).delete()
        if not deleted:
            return APIResponse.error(message="Listing not found.", status=status.HTTP_404_NOT_FOUND)
        return APIResponse.success(message="Listing removed.", status=status.HTTP_200_OK)