from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from django.core.cache import cache
from common.responses import APIResponse
from common.geocoding import geocode_address
from .models import Listing, ListingImage, ListingCategory
from .serializers import ListingSerializer, ListingCreateSerializer, ListingCategorySerializer, BookingSerializer, RentalSerializer
from django.contrib.auth import get_user_model
import razorpay
from django.conf import settings
from .models import Booking
from rag.services import index_listing
from notifications.services import send_push_notification, NotificationService

User = get_user_model()


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class ListingCategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cached = cache.get("listing_categories")
        if cached is not None:
            return APIResponse.success(
                data=cached, message="Categories fetched.", status=200
            )
        categories = ListingCategory.objects.filter(is_active=True)
        data = ListingCategorySerializer(categories, many=True).data
        cache.set("listing_categories", data, timeout=3600)
        return APIResponse.success(
            data=ListingCategorySerializer(categories, many=True).data,
            message="Categories fetched.", status=status.HTTP_200_OK,
        )

class ListingListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def post(self, request):
        serializer = ListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save(owner=request.user)

        coords = geocode_address(listing.location) if listing.location else None
        if coords:
            listing.latitude, listing.longitude = coords
            listing.save(update_fields=["latitude", "longitude"])

        for img in request.FILES.getlist("images"):
            ListingImage.objects.create(listing=listing, image=img)

        index_listing(listing)  # embed listing for RAG semantic search

        return APIResponse.success(
            data=ListingSerializer(listing, context={"request": request}).data,
            message="Listing created.", status=status.HTTP_201_CREATED,
        )

    def get(self, request):
        listings = Listing.objects.filter(is_active=True)
        if request.user.is_authenticated:
            listings = listings.exclude(owner=request.user)
        search = request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q
            words = [w.strip() for w in search.split() if w.strip()]
            q = Q()
            for word in words:
                q &= Q(title__icontains=word) | Q(description__icontains=word)
            listings = listings.filter(q)
        listings = listings.order_by("-created_at")
        return APIResponse.success(
            data=ListingSerializer(listings, many=True, context={"request": request}).data,
            message="Listings fetched.", status=status.HTTP_200_OK,
        )


class ListingDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, listing_id):
        try:
            listing = Listing.objects.get(id=listing_id)
        except Listing.DoesNotExist:
            return APIResponse.error(message="Listing not found.", status=status.HTTP_404_NOT_FOUND)
        return APIResponse.success(
            data=ListingSerializer(listing, context={"request": request}).data,
            message="Listing fetched.", status=status.HTTP_200_OK,
        )

    def patch(self, request, listing_id):
        listing = Listing.objects.filter(id=listing_id, owner=request.user).first()
        if not listing:
            return APIResponse.error(message="Listing not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = ListingCreateSerializer(listing, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save()
        if listing.location:
            coords = geocode_address(listing.location)
            if coords:
                listing.latitude, listing.longitude = coords
                listing.save(update_fields=["latitude", "longitude"])

        index_listing(listing)  # re-embed listing after update

        return APIResponse.success(
            data=ListingSerializer(listing, context={"request": request}).data,
            message="Listing updated.", status=status.HTTP_200_OK,
        )

    def delete(self, request, listing_id):
        deleted, _ = Listing.objects.filter(id=listing_id, owner=request.user).delete()
        if not deleted:
            return APIResponse.error(message="Listing not found.", status=status.HTTP_404_NOT_FOUND)
        # ListingEmbedding is auto-deleted via CASCADE on the listing FK
        return APIResponse.success(message="Listing deleted.", status=status.HTTP_200_OK)



class MyListingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        listings = Listing.objects.filter(owner=request.user).order_by("-created_at")
        return APIResponse.success(
            data=ListingSerializer(listings, many=True, context={"request": request}).data,
            message="Your listings fetched.", status=status.HTTP_200_OK,
        )



class SellerListingsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, user_id):
        try:
            seller = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return APIResponse.error(message="User not found.", status=404)
        listings = Listing.objects.filter(owner=seller, is_active=True).order_by("-created_at")
        return APIResponse.success(data={
            "seller_name": seller.full_name,
            "seller_email": seller.email,
            "seller_phone": seller.phone_number,
            "joined": seller.created_at,
            "listings": ListingSerializer(listings, many=True).data,
        }, message="Seller listings fetched.", status=200)



class CreateBookingOrderView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, listing_id):
        try:
            listing = Listing.objects.get(id=listing_id)
        except Listing.DoesNotExist:
            return APIResponse.error(message="Listing not found.", status=404)

        amount_paise = int(listing.price_per_week * 100)
        order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
        })

        booking = Booking.objects.create(
            listing=listing,
            renter=request.user,
            amount=listing.price_per_week,
            razorpay_order_id=order["id"],
            rental_start_date=listing.available_from,
            rental_end_date=listing.available_to,
        )

        return APIResponse.success(data={
            "booking_id": str(booking.id),
            "razorpay_order_id": order["id"],
            "amount": amount_paise,
            "key_id": settings.RAZORPAY_KEY_ID,
        }, message="Order created.", status=201)


class VerifyBookingPaymentView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        data = request.data
        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": data["razorpay_order_id"],
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature"],
            })
        except razorpay.errors.SignatureVerificationError:
            return APIResponse.error(message="Payment verification failed.", status=400)

        try:
            booking = Booking.objects.get(razorpay_order_id=data["razorpay_order_id"], renter=request.user)
        except Booking.DoesNotExist:
            return APIResponse.error(message="Booking not found.", status=404)

        booking.razorpay_payment_id = data["razorpay_payment_id"]
        booking.status = "PAID"
        booking.save()
        booking.listing.is_active = False
        booking.listing.save(update_fields=["is_active"])

        send_push_notification.delay(
            booking.listing.owner_id,
            "Booking Paid",
            f"Your listing \"{booking.listing.title[:50]}\" has been booked and paid.",
        )
        NotificationService.create_notification(
            booking.listing.owner_id,
            "Booking Paid",
            f"Your listing \"{booking.listing.title[:50]}\" has been booked and paid.",
        )

        return APIResponse.success(data=BookingSerializer(booking).data, message="Payment verified.", status=200)


class MyRentalsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rentals = (
            Booking.objects.filter(renter=request.user)
            .select_related("listing", "listing__category", "listing__owner")
            .prefetch_related("listing__images")
            .order_by("-created_at")
        )
        return APIResponse.success(
            data=RentalSerializer(rentals, many=True, context={"request": request}).data,
            message="Your rentals fetched.", status=status.HTTP_200_OK,
        )