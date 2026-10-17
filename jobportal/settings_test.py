"""Settings for the test suite: production settings plus a few test-only tweaks."""
import os

# Tests must not depend on a developer's .env file
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

from .settings import *  # noqa: E402,F401,F403
from .settings import MIDDLEWARE, STORAGES  # noqa: E402

# The real password hasher is deliberately slow; tests don't need that
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Serve static files without collectstatic and skip WhiteNoise in tests
STORAGES = {
    **STORAGES,
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
MIDDLEWARE = [m for m in MIDDLEWARE if m != 'whitenoise.middleware.WhiteNoiseMiddleware']

# The test client talks plain HTTP
SECURE_SSL_REDIRECT = False
