import re
from django.core.exceptions import ValidationError


def validate_phone_number(value):
    pattern = r"^\+?[1-9]\d{9,14}$"
    if not re.match(pattern, value):
        raise ValidationError("Enter a valid phone number (10-15 digits, optional +country code).")


def validate_strong_password(value):
    if len(value) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", value):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", value):
        raise ValidationError("Password must contain at least one digit.")
    if not re.search(r"[@$!%*?&#]", value):
        raise ValidationError("Password must contain at least one special character.")


def validate_full_name(value):
    if not re.match(r"^[A-Za-z ]{2,50}$", value):
        raise ValidationError("Name must contain only letters and spaces (2-50 characters).")
    

def validate_document_file(file):
    """Validates uploaded KYC documents (license, PAN, etc.) — size and type."""
    max_size_mb = 5
    allowed_extensions = ["pdf", "jpg", "jpeg", "png"]

    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size must not exceed {max_size_mb}MB.")

    ext = file.name.split(".")[-1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}.")


def validate_image_file(file):
    """Validates profile/identity images specifically."""
    max_size_mb = 5
    allowed_extensions = ["jpg", "jpeg", "png"]

    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Image size must not exceed {max_size_mb}MB.")

    ext = file.name.split(".")[-1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f"Unsupported image type. Allowed: {', '.join(allowed_extensions)}.")
