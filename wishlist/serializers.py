from rest_framework import serializers
from .models import Wishlist
from listings.models import Listing


class ListingMiniSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Listing
        fields = ["id", "title", "price_per_week", "location", "images", "category_name", "created_at"]

    def get_images(self, obj):
        request = self.context.get("request")
        return [
            {"image": request.build_absolute_uri(img.image.url) if request else img.image.url}
            for img in obj.images.all()
        ]


class WishlistSerializer(serializers.ModelSerializer):
    listing = ListingMiniSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "listing", "created_at"]