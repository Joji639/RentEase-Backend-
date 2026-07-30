from django.shortcuts import render

# Create your views here.
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Wishlist
from .serializers import WishlistSerializer
from listings.models import Listing


class WishlistListView(generics.ListAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Wishlist.objects.filter(user=self.request.user)
            .select_related("listing", "listing__category")
            .prefetch_related("listing__images")
        )


class WishlistToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, listing_id):
        listing = Listing.objects.filter(id=listing_id).first()
        if not listing:
            return Response({"message": "Listing not found"}, status=status.HTTP_404_NOT_FOUND)

        item = Wishlist.objects.filter(user=request.user, listing=listing).first()
        if item:
            item.delete()
            return Response({"wishlisted": False}, status=status.HTTP_200_OK)

        Wishlist.objects.create(user=request.user, listing=listing)
        return Response({"wishlisted": True}, status=status.HTTP_201_CREATED)