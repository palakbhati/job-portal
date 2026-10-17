from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from .validators import validate_file_size
# Create your models here.

class Job(models.Model):
    title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_posted = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-date_posted']

    def __str__(self):
        return self.title

class Application(models.Model):
    STATUS_APPLIED = 'applied'
    STATUS_REVIEWED = 'reviewed'
    STATUS_SHORTLISTED = 'shortlisted'
    STATUS_REJECTED = 'rejected'
    STATUS_HIRED = 'hired'
    STATUS_CHOICES = [
        (STATUS_APPLIED, 'Applied'),
        (STATUS_REVIEWED, 'Reviewed'),
        (STATUS_SHORTLISTED, 'Shortlisted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_HIRED, 'Hired'),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resume = models.FileField(
        upload_to='resumes/%Y/%m/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx']), validate_file_size],
    )
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_APPLIED)
    date_applied = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['job' , 'applicant']
    
    def __str__(self):
        return f"{self.applicant} applied to {self.job}"