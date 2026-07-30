from django.utils import timezone
from django.core.cache import cache
from django.db import models
from common.geocoding import haversine_km, estimate_price
from common.utils import generate_otp
from .models import ServiceRequest, ServicePart
from decimal import Decimal
from math import radians, sin, cos, sqrt, atan2
from decimal import ROUND_HALF_UP





PRICE_OTP_KEY = "arrival_otp:{rid}"


def calc_and_store_pricing(req: ServiceRequest):
    t = req.technician
    if t.latitude and t.longitude and req.user_latitude and req.user_longitude:
        dist = haversine_km(t.latitude, t.longitude, req.user_latitude, req.user_longitude)
        travel, service, total = estimate_price(t.hourly_rate or 0, dist)
        req.distance_km = dist
    else:
        travel, service, total = estimate_price(t.hourly_rate or 0, Decimal("0"))
        req.distance_km = Decimal("0")
    req.travel_cost = travel
    req.service_charge = service
    req.total_amount = total
    req.save(update_fields=["distance_km", "travel_cost", "service_charge", "total_amount"])
    return req


def issue_arrival_otp(req: ServiceRequest):
    otp = generate_otp(6)
    req.arrival_otp = otp
    req.otp_sent_at = timezone.now()
    req.status = "ARRIVED"
    req.save(update_fields=["arrival_otp", "otp_sent_at", "status"])
    cache.set(PRICE_OTP_KEY.format(rid=req.id), otp, timeout=600)
    return otp


def verify_arrival_otp(req: ServiceRequest, otp: str) -> bool:
    if req.arrival_otp and req.arrival_otp == otp and req.otp_sent_at:
        if (timezone.now() - req.otp_sent_at).total_seconds() <= 600:
            req.otp_verified = True
            req.status = "IN_PROGRESS"
            started_at = timezone.now()
            req.started_at = started_at
            req.work_started_at = started_at
            req.save(update_fields=["otp_verified", "status", "started_at", "work_started_at"])
            return True
    return False


def calculate_distance_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(lambda x: radians(float(x)), [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return Decimal(str(round(6371 * c, 2)))

def calculate_pricing(technician, distance_km, hours=Decimal("1")):
    km_rate = Decimal("5")
    travel_cost = distance_km * km_rate
    service_charge = (technician.hourly_rate or Decimal("0")) * Decimal(str(hours))
    service_charge = service_charge.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    travel_cost = travel_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = travel_cost + service_charge
    return travel_cost, service_charge, total


def get_approved_parts_total(req: ServiceRequest) -> Decimal:
    total = ServicePart.objects.filter(
        service_request=req, status=ServicePart.Status.APPROVED
    ).aggregate(total=models.Sum("total_price"))["total"]
    return total or Decimal("0")


def calculate_final_pricing(req: ServiceRequest, completed_at=None):
    completed_at = completed_at or timezone.now()
    duration_seconds = 0
    if req.work_started_at:
        duration_seconds = max((completed_at - req.work_started_at).total_seconds(), 0)
    hours = Decimal(str(duration_seconds)) / Decimal("3600")
    travel_cost, service_charge, total = calculate_pricing(
        req.technician, req.distance_km or Decimal("0"), hours
    )
    parts_total = get_approved_parts_total(req)
    req.travel_cost = travel_cost
    req.service_charge = service_charge
    req.total_amount = total + parts_total
    req.completed_at = completed_at
    req.save(update_fields=["travel_cost", "service_charge", "total_amount", "completed_at"])
    return req


def notify_user(user_id, event_type, request_id=None, **extra):
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    payload = {"type": "notification", "event": event_type, "request_id": str(request_id) if request_id else None}
    payload.update(extra)
    try:
        async_to_sync(channel_layer.group_send)(f"notify_{user_id}", payload)
    except Exception:
        pass


def notify_all_admins(event_type, **extra):
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    payload = {"type": "notification", "event": event_type}
    payload.update(extra)
    try:
        async_to_sync(channel_layer.group_send)("notify_admin", payload)
    except Exception:
        pass


def notify_all_technician_watchers(event_type, **extra):
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    payload = {"type": "notification", "event": event_type}
    payload.update(extra)
    try:
        async_to_sync(channel_layer.group_send)("technician_updates", payload)
    except Exception:
        pass
