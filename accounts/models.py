from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('employer','Employer'),
        ('seeker','Job Seeker'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='seeker')

    @property
    def is_employer(self):
        return self.role == 'employer'

    @property
    def is_seeker(self):
        return self.role == 'seeker'

    def __str__(self):
        return self.username  
