from django.urls import path
from . import views

urlpatterns = [
    path('', views.JobListView.as_view(), name='job_list'),
    path('jobs/<int:pk>/', views.JobDetailView.as_view(), name='job_detail'),
    path('jobs/new/', views.JobCreateView.as_view(), name='job_create'),
    path('jobs/<int:pk>/edit/', views.JobUpdateView.as_view(), name='job_update'),
    path('jobs/<int:pk>/apply/', views.apply_to_job, name='apply_to_job'),
    path('jobs/<int:pk>/applicants/', views.JobApplicantsView.as_view(), name='job_applicants'),
    path('applications/<int:pk>/status/', views.update_application_status, name='update_application_status'),
    path('applications/<int:pk>/resume/', views.download_resume, name='download_resume'),
    path('my-jobs/', views.MyJobsListView.as_view(), name='my_jobs'),
    path('my-applications/', views.MyApplicationListView.as_view(), name='my_applications'),
]
