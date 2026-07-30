import requests
import time
import threading
from decimal import Decimal
from math import radians, sin, cos, asin, sqrt
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.mail import send_mail
from django.conf import settings
from .models import ServiceRequest

STEPS = 25
INTERVAL_SECONDS = 2
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(float(lat2) - float(lat1))
    dlon = radians(float(lon2) - float(lon1))
    a = sin(dlat / 2) ** 2 + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(dlon / 2) ** 2
    return R * 2 * asin(sqrt(a))


def get_osrm_route(start_lat, start_lng, end_lat, end_lng):
    """
    Fetch a real driving route from OSRM.
    Returns (route_coords_km, total_distance_m, total_duration_s) or (None, None, None) on failure.
    route_coords_km: list of (lat, lng) tuples along the road path.
    """
    try:
        url = f"{OSRM_URL}/{start_lng},{start_lat};{end_lng},{end_lat}"
        params = {"geometries": "geojson", "overview": "full", "steps": "false"}
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            coords = route["geometry"]["coordinates"]
            latlngs = [(Decimal(str(c[1])), Decimal(str(c[0]))) for c in coords]
            return latlngs, route["distance"], route["duration"]
    except Exception:
        pass
    return None, None, None


def interpolate_route_position(route_coords, fraction):
    """Return (lat, lng) along route_coords at fraction [0,1] using cumulative distance."""
    if fraction >= 1 or len(route_coords) < 2:
        return float(route_coords[-1][0]), float(route_coords[-1][1])
    if fraction <= 0:
        return float(route_coords[0][0]), float(route_coords[0][1])
    distances = [Decimal("0")]
    for i in range(1, len(route_coords)):
        d = _haversine_km(route_coords[i - 1][0], route_coords[i - 1][1],
                          route_coords[i][0], route_coords[i][1])
        distances.append(distances[-1] + Decimal(str(d)))
    total_d = distances[-1]
    if total_d == 0:
        return float(route_coords[0][0]), float(route_coords[0][1])
    target_d = Decimal(str(fraction)) * total_d
    for i in range(1, len(distances)):
        if distances[i] >= target_d:
            seg_frac = float((target_d - distances[i - 1]) / (distances[i] - distances[i - 1]))
            lat = float(route_coords[i - 1][0]) + (float(route_coords[i][0]) - float(route_coords[i - 1][0])) * seg_frac
            lng = float(route_coords[i - 1][1]) + (float(route_coords[i][1]) - float(route_coords[i - 1][1])) * seg_frac
            return lat, lng
    return float(route_coords[-1][0]), float(route_coords[-1][1])


def simulate_technician_movement(request_id):
    req = ServiceRequest.objects.get(id=request_id)
    if not (req.technician.latitude and req.technician.longitude and req.user_latitude and req.user_longitude):
        return

    start_lat = float(req.technician.latitude)
    start_lng = float(req.technician.longitude)
    end_lat = float(req.user_latitude)
    end_lng = float(req.user_longitude)
    channel_layer = get_channel_layer()
    group_name = f"tracking_{request_id}"

    route_coords, total_distance_m, total_duration_s = get_osrm_route(start_lat, start_lng, end_lat, end_lng)

    if not route_coords:
        route_coords = [
            (Decimal(str(start_lat)), Decimal(str(start_lng))),
            (Decimal(str(end_lat)), Decimal(str(end_lng))),
        ]

    route_coords_float = [(float(lat), float(lng)) for lat, lng in route_coords]

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "location_update",
            "route_coords": route_coords_float,
            "total_distance_m": total_distance_m,
            "total_duration_s": total_duration_s,
            "latitude": route_coords_float[0][0],
            "longitude": route_coords_float[0][1],
        },
    )

    for step in range(1, STEPS + 1):
        fraction = step / STEPS
        lat, lng = interpolate_route_position(route_coords, fraction)

        req.current_tech_latitude = lat
        req.current_tech_longitude = lng
        req.save(update_fields=["current_tech_latitude", "current_tech_longitude"])

        remaining_dist = (total_distance_m * (1 - fraction)) if total_distance_m else None
        remaining_dur = (total_duration_s * (1 - fraction)) if total_duration_s else None

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "location_update",
                "latitude": lat,
                "longitude": lng,
                "arrived": step == STEPS,
                "remaining_distance_m": remaining_dist,
                "remaining_duration_s": remaining_dur,
            },
        )
        time.sleep(INTERVAL_SECONDS)


def simulate_technician_movement_async(request_id):
    t = threading.Thread(target=simulate_technician_movement, args=(request_id,), daemon=True)
    t.start()

def send_arrival_otp_email(email, otp, full_name):
    try:
        send_mail(
            subject="RentEase — Technician Arrived (Start OTP)",
            message=(
                f"Hi {full_name},\n\n"
                f"Your technician has reached the location.\n"
                f"Share this OTP to start the service: {otp}\n"
                f"This OTP is valid for 10 minutes.\n\n"
                f"— RentEase Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        pass