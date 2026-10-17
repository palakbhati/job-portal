import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from .mixins import EmployerRequiredMixin, SeekerRequiredMixin, employer_required, seeker_required
from .models import Job, Application
from .forms import Jobform, ApplicationForm


class JobListView(ListView):
    model = Job
    template_name = 'jobs/job_list.html'
    context_object_name = "all_jobs"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        location = self.request.GET.get('location', '').strip()
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(company_name__icontains=q) | Q(description__icontains=q)
            )
        if location:
            queryset = queryset.filter(location__icontains=location)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '').strip()
        context['location'] = self.request.GET.get('location', '').strip()
        return context


class JobDetailView(DetailView):
    model = Job
    template_name = 'jobs/job_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['application'] = Application.objects.filter(
                job=self.object, applicant=self.request.user
            ).first()
            if self.object.posted_by == self.request.user:
                context['applicant_count'] = self.object.application_set.count()
        return context


class JobCreateView(EmployerRequiredMixin, CreateView):
    model = Job
    form_class = Jobform
    template_name = 'jobs/job_form.html'
    success_url = reverse_lazy('my_jobs')

    def form_valid(self, form):
        form.instance.posted_by = self.request.user
        messages.success(self.request, "Job posted successfully.")
        return super().form_valid(form)


class JobUpdateView(EmployerRequiredMixin, UpdateView):
    model = Job
    form_class = Jobform
    template_name = 'jobs/job_form.html'
    success_url = reverse_lazy('my_jobs')

    def get_queryset(self):
        # Users can only edit jobs they posted; others get a 404
        return Job.objects.filter(posted_by=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Job updated successfully.")
        return super().form_valid(form)


class MyJobsListView(EmployerRequiredMixin, ListView):
    model = Job
    template_name = 'jobs/my_jobs.html'
    context_object_name = "my_jobs"

    def get_queryset(self):
        return Job.objects.filter(posted_by=self.request.user).annotate(
            applicant_count=Count('application'),
            new_count=Count('application', filter=Q(application__status=Application.STATUS_APPLIED)),
        )


class JobApplicantsView(EmployerRequiredMixin, ListView):
    model = Application
    template_name = 'jobs/job_applicants.html'
    context_object_name = "applications"

    def get_queryset(self):
        # 404 unless the job belongs to the logged-in employer
        self.job = get_object_or_404(Job, pk=self.kwargs['pk'], posted_by=self.request.user)
        queryset = self.job.application_set.select_related('applicant').order_by('-date_applied')
        status = self.request.GET.get('status')
        if status in dict(Application.STATUS_CHOICES):
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        counts = {
            row['status']: row['n']
            for row in self.job.application_set.values('status').annotate(n=Count('id'))
        }
        context['job'] = self.job
        context['status_choices'] = Application.STATUS_CHOICES
        context['status_counts'] = [
            (value, label, counts.get(value, 0)) for value, label in Application.STATUS_CHOICES
        ]
        context['total_count'] = sum(counts.values())
        context['current_status'] = self.request.GET.get('status', '')
        return context


@login_required
@seeker_required
def apply_to_job(request, pk):
    job = get_object_or_404(Job, pk=pk)

    if Application.objects.filter(job=job, applicant=request.user).exists():
        messages.info(request, "You have already applied to this job.")
        return redirect('job_detail', pk=job.pk)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = request.user
            application.save()
            messages.success(request, f"Your application for {job.title} has been submitted.")
            return redirect('my_applications')
    else:
        form = ApplicationForm()

    return render(request, 'jobs/job_apply.html', {'job': job, 'form': form})


@login_required
@employer_required
@require_POST
def update_application_status(request, pk):
    application = get_object_or_404(Application, pk=pk, job__posted_by=request.user)
    status = request.POST.get('status')
    if status in dict(Application.STATUS_CHOICES):
        application.status = status
        application.save(update_fields=['status', 'updated_at'])
        messages.success(
            request, f"{application.applicant.username} marked as {application.get_status_display()}."
        )
    else:
        messages.error(request, "Invalid status.")
    return redirect('job_applicants', pk=application.job.pk)


@login_required
def download_resume(request, pk):
    # Only the applicant and the employer who posted the job can see a resume
    application = get_object_or_404(
        Application.objects.select_related('job'),
        Q(applicant=request.user) | Q(job__posted_by=request.user),
        pk=pk,
    )
    resume = application.resume
    if not resume or not resume.storage.exists(resume.name):
        raise Http404("Resume not found.")
    return FileResponse(resume.open('rb'), filename=os.path.basename(resume.name))


class MyApplicationListView(SeekerRequiredMixin, ListView):
    model = Application
    template_name = 'jobs/my_applications.html'
    context_object_name = "my_applications"

    def get_queryset(self):
        return (
            Application.objects.filter(applicant=self.request.user)
            .select_related('job')
            .order_by('-date_applied')
        )
