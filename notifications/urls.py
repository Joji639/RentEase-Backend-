from django.urls import path
from . import views

urlpatterns = [
    path("subscribe/", views.SubscribeView.as_view(), name="push-subscribe"),
    path("", views.NotificationListView.as_view(), name="notification-list"),
]
