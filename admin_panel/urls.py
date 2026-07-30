from django.urls import path
from .views import (
    AdminPendingTechniciansView, AdminApproveTechnicianView, AdminRejectTechnicianView,
    AdminServiceCategoryListCreateView, AdminServiceCategoryDetailView, AdminServiceCategoryToggleActiveView,
)
from .views import AdminAllTechniciansView, AdminTechnicianDetailView
from .views import AdminUserListView, AdminUserDetailView
from .views import AdminListingCategoryListCreateView, AdminListingCategoryDetailView,AdminListingListView, AdminListingDetailView


urlpatterns = [
    # Technician approvals (existing)
    path("technicianspending/", AdminPendingTechniciansView.as_view(), name="admin-pending-technicians"),
    path("technicians/<uuid:technician_id>/approve/", AdminApproveTechnicianView.as_view(), name="admin-approve-technician"),
    path("technicians/<uuid:technician_id>/reject/", AdminRejectTechnicianView.as_view(), name="admin-reject-technician"),

    # Service category management (new)
    path("categories/", AdminServiceCategoryListCreateView.as_view(), name="admin-categories-list-create"),
    path("categories/<uuid:category_id>/", AdminServiceCategoryDetailView.as_view(), name="admin-category-detail"),
    path("categories/<uuid:category_id>/toggle-active/", AdminServiceCategoryToggleActiveView.as_view(), name="admin-category-toggle"),
    path("technicians/", AdminAllTechniciansView.as_view(), name="admin-all-technicians"),
    path("technicians/<uuid:technician_id>/", AdminTechnicianDetailView.as_view(), name="admin-technician-detail"),
    path("users/", AdminUserListView.as_view(), name="admin-users-list"),
    path("users/<uuid:user_id>/", AdminUserDetailView.as_view(), name="admin-user-detail"),


    path("listing-categories/", AdminListingCategoryListCreateView.as_view(), name="admin-listing-categories"),
    path("listing-categories/<uuid:category_id>/", AdminListingCategoryDetailView.as_view(), name="admin-listing-category-detail"),
    path("listings/", AdminListingListView.as_view(), name="admin-listings"),
    path("listings/<uuid:listing_id>/", AdminListingDetailView.as_view(), name="admin-listing-detail"),
]