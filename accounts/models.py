from django.db import models
import uuid   #36 character string 
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import CustomUserManager     


class RoleChoices(models.TextChoices):
    USER = "USER", "User"
    TECHNICIAN = "TECHNICIAN", "Technician"
    ADMIN = "ADMIN", "Admin"


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.USER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, null=True, blank=True)
    latest_location = models.CharField(max_length=255, blank=True)
    latest_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latest_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    
    objects = CustomUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        permissions = [
            ("can_enable_2fa", "Can enable two-factor authentication"),
        ]

    def __str__(self):
        return self.email