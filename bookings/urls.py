from django.urls import path
from .views import (
    CreateServiceRequestView, MyServiceRequestsView,
    TechnicianServiceRequestsView, ServiceRequestStatusView,
    PriceEstimateView, ArriveView, VerifyArrivalOtpView,
    PayServiceView, VerifyServicePaymentView, CancelServiceRequestView,
    ServicePartListCreateView, ServicePartApproveRejectView,
)

urlpatterns = [
    path("price-estimate/", PriceEstimateView.as_view(), name="price-estimate"),
    path("request/", CreateServiceRequestView.as_view(), name="create-service-request"),
    path("my-requests/", MyServiceRequestsView.as_view(), name="my-service-requests"),
    path("technician-requests/", TechnicianServiceRequestsView.as_view(), name="technician-service-requests"),
    path("<uuid:request_id>/status/", ServiceRequestStatusView.as_view(), name="service-request-status"),
    path("<uuid:request_id>/arrive/", ArriveView.as_view(), name="service-request-arrive"),
    path("<uuid:request_id>/verify-otp/", VerifyArrivalOtpView.as_view(), name="service-request-verify-otp"),
    path("<uuid:request_id>/pay/", PayServiceView.as_view(), name="service-request-pay"),
    path("<uuid:request_id>/cancel/", CancelServiceRequestView.as_view(), name="service-request-cancel"),
    path("<uuid:request_id>/parts/", ServicePartListCreateView.as_view(), name="service-part-list-create"),
    path("<uuid:request_id>/parts/<int:part_id>/", ServicePartApproveRejectView.as_view(), name="service-part-approve-reject"),
    path("pay/verify/", VerifyServicePaymentView.as_view(), name="service-request-pay-verify"),
]