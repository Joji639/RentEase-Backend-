import uuid
from django.db import models
from django.conf import settings

class ServiceRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        ARRIVED = "ARRIVED", "Arrived"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        PAID = "PAID", "Paid"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    PAYMENT_METHODS = [("CASH", "Cash"), ("ONLINE", "Online")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_requests")
    technician = models.ForeignKey("technicians.TechnicianProfile", on_delete=models.CASCADE, related_name="service_requests")
    category = models.ForeignKey("services.ServiceCategory", on_delete=models.SET_NULL, null=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(max_length=254, blank=True)
    phone_number = models.CharField(max_length=20)
    date = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    user_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_tech_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_tech_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # pricing
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    travel_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # arrival OTP
    arrival_otp = models.CharField(max_length=6, blank=True)
    otp_sent_at = models.DateTimeField(null=True, blank=True)
    otp_verified = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    work_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # payment
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, blank=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "service_requests"

    def __str__(self):
        return f"{self.user} → {self.technician} ({self.status})"


class ServicePart(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    service_request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name="parts"
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    part_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_parts"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.part_name} x{self.quantity} ({self.status})"
