from django.urls import path
from .views import PublicServiceCategoryListView

urlpatterns = [
    path("", PublicServiceCategoryListView.as_view(), name="service-categories-list"),
]