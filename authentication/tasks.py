from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_otp_email(self, email: str, otp: str, full_name: str):
    subject = "RentEase — Your Password Reset OTP"
    message = (
        f"Hi {full_name},\n\n"
        f"Your OTP to reset your password is: {otp}\n\n"
        f"This OTP is valid for {settings.PASSWORD_RESET_OTP_EXPIRY_MINUTES} minutes.\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"— RentEase Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def send_password_changed_notification(email: str, full_name: str):
    subject = "RentEase — Your Password Was Changed"
    message = (
        f"Hi {full_name},\n\n"
        f"Your password was successfully changed. If this wasn't you, "
        f"please contact support immediately.\n\n"
        f"— RentEase Team"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )