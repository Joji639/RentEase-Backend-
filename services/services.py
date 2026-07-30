from django.core.cache import cache
from common.exceptions import NotFoundException, ValidationException
from .models import ServiceCategory


class ServiceCategoryService:
    """Business logic for service category management."""

    @staticmethod
    def list_active_categories():
        cached = cache.get("service_categories")
        if cached is not None:
            return cached
        qs = list(ServiceCategory.objects.filter(is_active=True))
        cache.set("service_categories", qs, timeout=3600)
        return qs

    @staticmethod
    def list_all_categories():
        return ServiceCategory.objects.all()

    @staticmethod
    def get_category(category_id) -> ServiceCategory:
        try:
            return ServiceCategory.objects.get(id=category_id)
        except ServiceCategory.DoesNotExist:
            raise NotFoundException("Service category not found.")

    @staticmethod
    def create_category(validated_data: dict) -> ServiceCategory:
        name = validated_data.get("name", "").strip()
        if ServiceCategory.objects.filter(name__iexact=name).exists():
            raise ValidationException("A service category with this name already exists.")
        return ServiceCategory.objects.create(**validated_data)

    @staticmethod
    def update_category(category_id, validated_data: dict) -> ServiceCategory:
        category = ServiceCategoryService.get_category(category_id)

        new_name = validated_data.get("name")
        if new_name and new_name.strip().lower() != category.name.lower():
            if ServiceCategory.objects.filter(name__iexact=new_name.strip()).exists():
                raise ValidationException("A service category with this name already exists.")

        for field, value in validated_data.items():
            setattr(category, field, value)
        category.save()
        return category

    @staticmethod
    def delete_category(category_id) -> None:
        category = ServiceCategoryService.get_category(category_id)
        category.delete()

    @staticmethod
    def toggle_active(category_id) -> ServiceCategory:
        category = ServiceCategoryService.get_category(category_id)
        category.is_active = not category.is_active
        category.save(update_fields=["is_active"])
        return category