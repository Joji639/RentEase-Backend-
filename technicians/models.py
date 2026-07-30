from django.db import models

# Create your models here.
import uuid
from django.db import models
from django.conf import settings


class VerificationStatus(models.TextChoices):
    NOT_SUBMITTED = "NOT_SUBMITTED", "Not Submitted"
    PENDING = "PENDING", "Pending Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class TechnicianProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="technician_profile",
    )

    specialization = models.ForeignKey("services.ServiceCategory",on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name="technicians",)
    experience_years = models.PositiveIntegerField(null=True, blank=True)
    service_area = models.CharField(max_length=150, blank=True)
    address = models.CharField(max_length=255, blank=True)

    profile_image = models.ImageField(upload_to="technicians/profile_images/", null=True, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    license_document = models.FileField(upload_to="technicians/licenses/", null=True, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    pan_card_document = models.FileField(upload_to="technicians/pan_cards/", null=True, blank=True)
    certification_document = models.FileField(upload_to="technicians/certifications/", null=True, blank=True)

    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.NOT_SUBMITTED
    )
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviewed_technicians",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    class Meta:
        db_table = "technician_profiles"
        verbose_name = "Technician Profile"
        verbose_name_plural = "Technician Profiles"

    def __str__(self):
        return f"{self.user.email} - {self.verification_status}"

    def is_onboarding_complete(self) -> bool:
        return bool(
            self.license_number and self.license_document
            and self.pan_number and self.pan_card_document
        )