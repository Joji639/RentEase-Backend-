from django.urls import path
from .views import TechnicianRegisterView, TechnicianOnboardingView, TechnicianProfileView,TechniciansByCategoryView

urlpatterns = [
    path("register/", TechnicianRegisterView.as_view(), name="technician-register"),
    path("onboarding/", TechnicianOnboardingView.as_view(), name="technician-onboarding"),
    path("profile/", TechnicianProfileView.as_view(), name="technician-profile"),
    path("by-category/<uuid:category_id>/", TechniciansByCategoryView.as_view(), name="technicians-by-category"),
]