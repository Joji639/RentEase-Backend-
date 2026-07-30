# pyrefly: ignore [missing-import]
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
# pyrefly: ignore [missing-import]
from django.utils import timezone
# pyrefly: ignore [missing-import]
import razorpay
# pyrefly: ignore [missing-import]
from django.conf import settings
from common.responses import APIResponse
from common.permissions import IsTechnician
from common.geocoding import haversine_km, estimate_price, geocode_address
from .models import ServiceRequest, ServicePart
from .serializers import (
    ServiceRequestSerializer, ServiceRequestCreateSerializer,
    ServiceRequestStatusSerializer, PriceEstimateSerializer,
    VerifyArrivalOtpSerializer, PayServiceSerializer, VerifyOtpSerializer,
    ServicePartSerializer, ServicePartApprovalSerializer,
)
from .services import calc_and_store_pricing, issue_arrival_otp, verify_arrival_otp, calculate_distance_km, calculate_pricing, calculate_final_pricing, get_approved_parts_total, notify_user
from django.http import Http404
from .tasks import send_arrival_otp_email, simulate_technician_movement_async
from technicians.models import TechnicianProfile
from notifications.services import send_push_notification, NotificationService

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class PriceEstimateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PriceEstimateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            tech = TechnicianProfile.objects.get(id=d["technician"])
        except TechnicianProfile.DoesNotExist:
            return APIResponse.error(message="Technician not found.", status=status.HTTP_404_NOT_FOUND)
        if not (tech.latitude and tech.longitude):
            return APIResponse.error(message="Technician location not set.", status=status.HTTP_400_BAD_REQUEST)

        distance_km = calculate_distance_km(tech.latitude, tech.longitude, d["user_latitude"], d["user_longitude"])
        travel_cost, service_charge, total = calculate_pricing(tech, distance_km)

        return APIResponse.success(data={
            "distance_km": str(distance_km),
            "travel_cost": str(travel_cost),
            "service_charge": str(service_charge),
            "total_amount": str(total),
            "hourly_rate": str(tech.hourly_rate),
            "km_rate": 5,
        }, message="Estimate calculated.", status=status.HTTP_200_OK)

class CreateServiceRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = ServiceRequestCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        lat = request.data.get("user_latitude")
        lng = request.data.get("user_longitude")
        address = data.get("address", "")

        if address and not (lat and lng):
            coords = geocode_address(address)
            if not coords:
                return APIResponse.error(message="Address could not be geocoded. Please provide a more specific address.", status=status.HTTP_400_BAD_REQUEST)
            lat, lng = coords

        req = s.save(user=request.user, user_latitude=lat, user_longitude=lng)
        calc_and_store_pricing(req)
        notify_user(req.technician.user_id, "new_request", req.id)
        NotificationService.create_notification(
            req.technician.user_id,
            "New Service Request",
            f"A new {req.category.name if req.category else 'service'} request has been created.",
        )
        return APIResponse.success(
            data=ServiceRequestSerializer(req).data,
            message="Service request sent.", status=status.HTTP_201_CREATED,
        )

class MyServiceRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reqs = ServiceRequest.objects.filter(user=request.user).order_by("-created_at")
        return APIResponse.success(
            data=ServiceRequestSerializer(reqs, many=True).data,
            message="Your requests fetched.", status=status.HTTP_200_OK,
        )

class TechnicianServiceRequestsView(APIView):
    permission_classes = [IsAuthenticated, IsTechnician]

    def get(self, request):
        reqs = ServiceRequest.objects.filter(technician__user=request.user).order_by("-created_at")
        return APIResponse.success(
            data=ServiceRequestSerializer(reqs, many=True).data,
            message="Requests fetched.", status=status.HTTP_200_OK,
        )

class ServiceRequestStatusView(APIView):
    permission_classes = [IsAuthenticated, IsTechnician]

    def patch(self, request, request_id):
        req = ServiceRequest.objects.filter(id=request_id, technician__user=request.user).first()
        if not req:
            return APIResponse.error(message="Request not found.", status=status.HTTP_404_NOT_FOUND)

        s = ServiceRequestStatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        new = s.validated_data["status"]
        req.status = new
        if new == "ACCEPTED":
            simulate_technician_movement_async(str(req.id))
            notify_user(req.user_id, "accepted", req.id)
            send_push_notification.delay(req.user_id, "Request Accepted", f"Your {req.category.name if req.category else 'service'} request has been accepted by a technician.")
            NotificationService.create_notification(
                req.user_id,
                "Request Accepted",
                f"Your {req.category.name if req.category else 'service'} request has been accepted.",
            )
            NotificationService.create_notification(
                req.technician.user_id,
                "Request Accepted",
                f"You accepted {req.full_name or 'a customer'}'s {req.category.name or 'service'} request.",
            )
            notify_user(req.technician.user_id, "accepted", req.id)
        elif new == "COMPLETED":
            calculate_final_pricing(req, timezone.now())
            req.status = new
            req.save(update_fields=["status"])
            notify_user(req.user_id, "completed", req.id, total_amount=str(req.total_amount))
            send_push_notification.delay(req.user_id, "Service Completed", f"Your service is complete. Total: ₹{req.total_amount}.")
            NotificationService.create_notification(
                req.user_id,
                "Service Completed",
                f"Service complete. Total: ₹{req.total_amount}.",
            )
            return APIResponse.success(
                data=ServiceRequestSerializer(req).data,
                message="Status updated and final price calculated.", status=status.HTTP_200_OK,
            )
        elif new == "REJECTED":
            notify_user(req.user_id, "rejected", req.id)
        req.save()
        return APIResponse.success(
            data=ServiceRequestSerializer(req).data,
            message="Status updated.", status=status.HTTP_200_OK,
        )

ARRIVAL_RADIUS_KM = 0.05  # 50 meters


class ArriveView(APIView):
    permission_classes = [IsAuthenticated, IsTechnician]

    def post(self, request, request_id):
        try:
            req = ServiceRequest.objects.get(id=request_id, technician__user=request.user)
        except ServiceRequest.DoesNotExist:
            return APIResponse.error(message="Request not found.", status=status.HTTP_404_NOT_FOUND)

        if req.status not in ("ACCEPTED", "ARRIVED"):
            return APIResponse.error(message="Cannot arrive in current status.", status=status.HTTP_400_BAD_REQUEST)

        tech_lat = req.current_tech_latitude or req.technician.latitude
        tech_lng = req.current_tech_longitude or req.technician.longitude
        if tech_lat and tech_lng and req.user_latitude and req.user_longitude:
            dist = haversine_km(float(tech_lat), float(tech_lng),
                                float(req.user_latitude), float(req.user_longitude))
            if dist > ARRIVAL_RADIUS_KM:
                return APIResponse.error(
                    message=f"You are {dist*1000:.0f}m away from the customer. Approach within {ARRIVAL_RADIUS_KM*1000:.0f}m to mark arrival.",
                    status=status.HTTP_400_BAD_REQUEST,
                )

        otp = issue_arrival_otp(req)
        recipient = req.email or req.user.email
        send_arrival_otp_email(recipient, otp, req.full_name or req.user.full_name)
        notify_user(req.user_id, "arrived", req.id)
        send_push_notification.delay(req.user_id, "Technician Arrived", "Your technician has arrived and an OTP has been sent.")
        NotificationService.create_notification(
            req.user_id,
            "Technician Arrived",
            "Your technician has arrived and an OTP has been sent.",
        )
        return APIResponse.success(message="Arrived. OTP sent to user.", status=status.HTTP_200_OK)


class VerifyArrivalOtpView(APIView):
    permission_classes = [IsAuthenticated, IsTechnician]

    def post(self, request, request_id):
        try:
            req = ServiceRequest.objects.get(id=request_id, technician__user=request.user)
        except ServiceRequest.DoesNotExist:
            return APIResponse.error(message="Request not found.", status=status.HTTP_404_NOT_FOUND)

        s = VerifyOtpSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if verify_arrival_otp(req, s.validated_data["otp"]):
            notify_user(req.user_id, "in_progress", req.id)
            return APIResponse.success(message="OTP verified. Service started.", status=status.HTTP_200_OK)
        return APIResponse.error(message="Incorrect or expired OTP.", status=status.HTTP_400_BAD_REQUEST)

class PayServiceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        try:
            req = ServiceRequest.objects.get(id=request_id)
        except ServiceRequest.DoesNotExist:
            return APIResponse.error(message="Request not found.", status=status.HTTP_404_NOT_FOUND)

        if req.status != "COMPLETED":
            return APIResponse.error(message="Service must be completed first.", status=status.HTTP_400_BAD_REQUEST)

        serializer = PayServiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        method = serializer.validated_data["payment_method"]

        if not req.total_amount:
            distance_km = calculate_distance_km(
                req.technician.latitude, req.technician.longitude, req.user_latitude, req.user_longitude
            )
            travel_cost, service_charge, total = calculate_pricing(req.technician, distance_km)
            parts_total = get_approved_parts_total(req)
            req.distance_km, req.travel_cost, req.service_charge, req.total_amount = distance_km, travel_cost, service_charge, total + parts_total
            req.save()

        if method == "CASH":
            req.payment_method = "CASH"
            req.status = "PAID"
            req.completed_at = timezone.now()
            req.save(update_fields=["payment_method", "status", "completed_at"])
            notify_user(req.technician.user_id, "paid", req.id, payment_method="CASH")
            return APIResponse.success(message="Marked as cash collection.", status=status.HTTP_200_OK)

        amount_paise = int(req.total_amount * 100)
        order = razorpay_client.order.create({
            "amount": amount_paise, "currency": "INR", "payment_capture": 1,
        })
        req.razorpay_order_id = order["id"]
        req.payment_method = "ONLINE"
        req.save(update_fields=["razorpay_order_id", "payment_method"])
        
        qr_payload = f"upi://pay?pa=rentease@upi&am={req.total_amount}&tn=RentEase-{req.id}"
        return APIResponse.success(data={
            "razorpay_order_id": order["id"], "amount": amount_paise,
            "key_id": settings.RAZORPAY_KEY_ID, "qr_payload": qr_payload,
        }, message="Payment order created.", status=status.HTTP_201_CREATED)

class VerifyServicePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        d = request.data
        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": d["razorpay_order_id"],
                "razorpay_payment_id": d["razorpay_payment_id"],
                "razorpay_signature": d["razorpay_signature"],
            })
        except razorpay.errors.SignatureVerificationError:
            return APIResponse.error(message="Payment verification failed.", status=status.HTTP_400_BAD_REQUEST)

        req = ServiceRequest.objects.filter(razorpay_order_id=d["razorpay_order_id"]).first()
        if not req:
            return APIResponse.error(message="Request not found.", status=status.HTTP_404_NOT_FOUND)
            
        req.razorpay_payment_id = d["razorpay_payment_id"]
        req.status = "PAID"
        req.completed_at = timezone.now()
        req.save(update_fields=["razorpay_payment_id", "status", "completed_at"])
        notify_user(req.technician.user_id, "paid", req.id, payment_method="ONLINE")
        return APIResponse.success(
            data=ServiceRequestSerializer(req).data,
            message="Payment verified.", status=status.HTTP_200_OK,
        )


class CancelServiceRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        try:
            req = ServiceRequest.objects.get(id=request_id, user=request.user)
        except ServiceRequest.DoesNotExist:
            raise Http404("Request not found.")

        if req.status in ("COMPLETED", "PAID", "CANCELLED", "REJECTED"):
            return APIResponse.error(
                message="This request can no longer be cancelled.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        req.status = "CANCELLED"
        req.save(update_fields=["status"])
        notify_user(req.technician.user_id, "cancelled", req.id)
        return APIResponse.success(
            message="Service request cancelled.",
            status=status.HTTP_200_OK,
        )


class ServicePartListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        req = ServiceRequest.objects.filter(id=request_id).first()
        if not req:
            return APIResponse.error(message="Request not found.", status=status.HTTP_404_NOT_FOUND)
        if req.user != request.user and req.technician.user != request.user:
            return APIResponse.error(message="Not your request.", status=status.HTTP_403_FORBIDDEN)
        parts = ServicePart.objects.filter(service_request=req).order_by("-created_at")
        return APIResponse.success(
            data=ServicePartSerializer(parts, many=True).data,
            message="Parts fetched.",
            status=status.HTTP_200_OK,
        )

    def post(self, request, request_id):
        req = ServiceRequest.objects.filter(id=request_id).first()
        if not req:
            return APIResponse.error(message="Request not found.", status=status.HTTP_404_NOT_FOUND)
        if req.technician.user != request.user:
            return APIResponse.error(message="Only the assigned technician can add parts.", status=status.HTTP_403_FORBIDDEN)
        if req.status not in ("IN_PROGRESS",):
            return APIResponse.error(message="Cannot add parts in current status.", status=status.HTTP_400_BAD_REQUEST)
        s = ServicePartSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        part = s.save(service_request=req, added_by=request.user)
        notify_user(req.user_id, "part_added", req.id)
        NotificationService.create_notification(
            req.user_id,
            "New Part Added",
            f"{part.part_name} — ₹{part.total_price} added by technician.",
        )
        return APIResponse.success(
            data=ServicePartSerializer(part).data,
            message="Part added.",
            status=status.HTTP_201_CREATED,
        )


class ServicePartApproveRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, request_id, part_id):
        req = ServiceRequest.objects.filter(id=request_id).first()
        if not req:
            return APIResponse.error(message="Request not found.", status=status.HTTP_404_NOT_FOUND)
        if req.user != request.user:
            return APIResponse.error(message="Only the service owner can approve/reject parts.", status=status.HTTP_403_FORBIDDEN)
        part = ServicePart.objects.filter(id=part_id, service_request=req).first()
        if not part:
            return APIResponse.error(message="Part not found.", status=status.HTTP_404_NOT_FOUND)
        if part.status != "PENDING":
            return APIResponse.error(message="Part already resolved.", status=status.HTTP_400_BAD_REQUEST)
        s = ServicePartApprovalSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        action = s.validated_data["action"]
        part.status = "APPROVED" if action == "APPROVE" else "REJECTED"
        part.save(update_fields=["status"])
        return APIResponse.success(
            data=ServicePartSerializer(part).data,
            message=f"Part {action.lower()}d.",
            status=status.HTTP_200_OK,
        )
