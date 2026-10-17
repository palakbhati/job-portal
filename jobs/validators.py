from django.core.exceptions import ValidationError

MAX_RESUME_SIZE_MB = 5


def validate_file_size(file):
    if file.size > MAX_RESUME_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"File too large. Maximum size is {MAX_RESUME_SIZE_MB} MB.")
