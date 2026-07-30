from django.urls import path
from .views import WishlistListView, WishlistToggleView

urlpatterns = [
    path("", WishlistListView.as_view(), name="wishlist-list"),
    path("<uuid:listing_id>/toggle/", WishlistToggleView.as_view(), name="wishlist-toggle"),
]