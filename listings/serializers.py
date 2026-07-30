from rest_framework import serializers
from .models import Listing, ListingImage, ListingCategory,Booking

class ListingCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingCategory
        fields = ["id", "name", "is_active"]

class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ["id", "image"]

class ListingSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True)
    owner_phone = serializers.CharField(source="owner.phone_number", read_only=True)
    owner_id = serializers.UUIDField(source="owner.id", read_only=True)
    owner_latest_latitude = serializers.DecimalField(source="owner.latest_latitude", max_digits=9, decimal_places=6, read_only=True)
    owner_latest_longitude = serializers.DecimalField(source="owner.latest_longitude", max_digits=9, decimal_places=6, read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id", "title", "description", "category", "category_name", "price_per_week",
            "location", "latitude", "longitude", "available_from", "available_to", "condition",
            "is_active", "created_at", "images", "owner", "owner_id", "owner_name","owner_email","owner_phone",
            "owner_latest_latitude", "owner_latest_longitude",
        ]
        read_only_fields = ["id", "owner", "created_at", "latitude", "longitude"]

class ListingCreateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ListingCategory.objects.filter(is_active=True))

    class Meta:
        model = Listing
        fields = [
            "title", "description", "category", "price_per_week",
            "location", "available_from", "available_to", "condition",
        ]



class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ["id", "listing", "amount", "razorpay_order_id", "status", "created_at"]
        read_only_fields = fields




class RentalListingMiniSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Listing
        fields = ["id", "title", "location", "category_name", "images", "owner_name", "owner_email"]


class RentalSerializer(serializers.ModelSerializer):
    listing = RentalListingMiniSerializer(read_only=True)
    rental_days = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id", "listing", "amount", "status",
            "rental_start_date", "rental_end_date", "rental_days", "created_at",
        ]
        read_only_fields = fields

    def get_rental_days(self, obj):
        if obj.rental_start_date and obj.rental_end_date:
            return (obj.rental_end_date - obj.rental_start_date).days
        return None