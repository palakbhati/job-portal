import pytest
from django.urls import reverse

from jobs.models import Application

pytestmark = pytest.mark.django_db


class TestApply:
    def test_apply_page_has_upload_form(self, login, seeker, job):
        response = login(seeker).get(reverse('apply_to_job', args=[job.pk]))
        assert response.status_code == 200
        assert b'multipart/form-data' in response.content

    def test_seeker_can_apply_with_resume(self, login, seeker, job, resume_file):
        response = login(seeker).post(
            reverse('apply_to_job', args=[job.pk]),
            {'resume': resume_file(), 'cover_letter': 'Hire me'},
        )
        assert response.status_code == 302
        assert response.url == reverse('my_applications')
        application = Application.objects.get()
        assert application.applicant == seeker
        assert application.job == job
        assert application.cover_letter == 'Hire me'
        assert application.status == Application.STATUS_APPLIED

    def test_resume_is_required(self, login, seeker, job):
        response = login(seeker).post(reverse('apply_to_job', args=[job.pk]), {})
        assert 'resume' in response.context['form'].errors
        assert not Application.objects.exists()

    def test_rejects_wrong_file_type(self, login, seeker, job, resume_file):
        response = login(seeker).post(
            reverse('apply_to_job', args=[job.pk]), {'resume': resume_file('virus.exe')}
        )
        assert 'resume' in response.context['form'].errors
        assert not Application.objects.exists()

    def test_rejects_file_over_5mb(self, login, seeker, job, resume_file):
        response = login(seeker).post(
            reverse('apply_to_job', args=[job.pk]), {'resume': resume_file(size=6 * 1024 * 1024)}
        )
        assert b'File too large' in response.content
        assert not Application.objects.exists()

    def test_cannot_apply_twice(self, login, seeker, application, resume_file):
        client = login(seeker)
        url = reverse('apply_to_job', args=[application.job.pk])
        response = client.post(url, {'resume': resume_file()})
        assert response.status_code == 302
        assert response.url == reverse('job_detail', args=[application.job.pk])
        assert Application.objects.count() == 1

    def test_apply_to_missing_job_returns_404(self, login, seeker):
        assert login(seeker).get(reverse('apply_to_job', args=[999])).status_code == 404


class TestMyApplications:
    def test_lists_only_own_applications(self, login, seeker, other_seeker, application, job, resume_file):
        Application.objects.create(job=job, applicant=other_seeker, resume=resume_file())
        response = login(seeker).get(reverse('my_applications'))
        assert list(response.context['my_applications']) == [application]
        assert b'status-applied' in response.content


class TestApplicants:
    def test_owner_sees_applicants(self, login, employer, application):
        response = login(employer).get(reverse('job_applicants', args=[application.job.pk]))
        assert response.status_code == 200
        assert list(response.context['applications']) == [application]
        assert response.context['total_count'] == 1
        assert b'I would love to join.' in response.content

    def test_filter_by_status(self, login, employer, application):
        client = login(employer)
        url = reverse('job_applicants', args=[application.job.pk])
        assert list(client.get(url, {'status': 'applied'}).context['applications']) == [application]
        assert list(client.get(url, {'status': 'hired'}).context['applications']) == []

    def test_status_tab_counts(self, login, employer, application):
        response = login(employer).get(reverse('job_applicants', args=[application.job.pk]))
        counts = {value: count for value, _, count in response.context['status_counts']}
        assert counts['applied'] == 1
        assert counts['hired'] == 0

    def test_unknown_status_filter_is_ignored(self, login, employer, application):
        response = login(employer).get(
            reverse('job_applicants', args=[application.job.pk]), {'status': 'bogus'}
        )
        assert list(response.context['applications']) == [application]

    def test_other_employer_gets_404(self, login, other_employer, application):
        response = login(other_employer).get(reverse('job_applicants', args=[application.job.pk]))
        assert response.status_code == 404


class TestUpdateStatus:
    def test_owner_can_update_status(self, login, employer, application):
        response = login(employer).post(
            reverse('update_application_status', args=[application.pk]), {'status': 'shortlisted'}
        )
        assert response.url == reverse('job_applicants', args=[application.job.pk])
        application.refresh_from_db()
        assert application.status == 'shortlisted'

    def test_invalid_status_is_rejected(self, login, employer, application):
        login(employer).post(
            reverse('update_application_status', args=[application.pk]), {'status': 'bogus'}
        )
        application.refresh_from_db()
        assert application.status == 'applied'

    def test_other_employer_cannot_update(self, login, other_employer, application):
        response = login(other_employer).post(
            reverse('update_application_status', args=[application.pk]), {'status': 'hired'}
        )
        assert response.status_code == 404
        application.refresh_from_db()
        assert application.status == 'applied'

    def test_get_is_not_allowed(self, login, employer, application):
        response = login(employer).get(reverse('update_application_status', args=[application.pk]))
        assert response.status_code == 405


class TestDownloadResume:
    def test_applicant_can_download(self, login, seeker, application):
        response = login(seeker).get(reverse('download_resume', args=[application.pk]))
        assert response.status_code == 200
        assert b''.join(response.streaming_content).startswith(b'%PDF')

    def test_job_owner_can_download(self, login, employer, application):
        response = login(employer).get(reverse('download_resume', args=[application.pk]))
        assert response.status_code == 200
        assert 'resume' in response['Content-Disposition']

    @pytest.mark.parametrize('intruder', ['other_seeker', 'other_employer'])
    def test_others_get_404(self, request, login, application, intruder):
        user = request.getfixturevalue(intruder)
        response = login(user).get(reverse('download_resume', args=[application.pk]))
        assert response.status_code == 404

    def test_anonymous_redirected_to_login(self, client, application):
        response = client.get(reverse('download_resume', args=[application.pk]))
        assert response.status_code == 302
        assert response.url.startswith(reverse('login'))

    def test_application_without_resume_returns_404(self, login, seeker, application):
        Application.objects.filter(pk=application.pk).update(resume='')
        response = login(seeker).get(reverse('download_resume', args=[application.pk]))
        assert response.status_code == 404

    def test_missing_file_returns_404(self, login, seeker, application):
        application.resume.delete(save=False)
        application.resume = 'resumes/gone.pdf'
        application.save()
        response = login(seeker).get(reverse('download_resume', args=[application.pk]))
        assert response.status_code == 404
