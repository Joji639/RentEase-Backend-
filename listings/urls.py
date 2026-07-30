from django.urls import path
from .views import ListingListCreateView, ListingDetailView, ListingCategoryListView, MyListingsView,SellerListingsView,CreateBookingOrderView, VerifyBookingPaymentView, MyRentalsView

urlpatterns = [
    path("", ListingListCreateView.as_view(), name="listing-list-create"),
    path("mine/", MyListingsView.as_view(), name="my-listings"),
    path("my-rentals/", MyRentalsView.as_view(), name="my-rentals"), 
    path("<uuid:listing_id>/", ListingDetailView.as_view(), name="listing-detail"),
    path("categories/", ListingCategoryListView.as_view(), name="listing-categories"),
    path("user/<uuid:user_id>/", SellerListingsView.as_view(), name="seller-listings"),
    path("<uuid:listing_id>/book/", CreateBookingOrderView.as_view(), name="create-booking-order"),
    path("bookings/verify/", VerifyBookingPaymentView.as_view(), name="verify-booking-payment"),
]