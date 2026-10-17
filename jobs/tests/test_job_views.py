import pytest
from django.urls import reverse

from jobs.models import Job

pytestmark = pytest.mark.django_db


class TestJobList:
    def test_lists_jobs(self, client, job):
        response = client.get(reverse('job_list'))
        assert response.status_code == 200
        assert job in response.context['all_jobs']
        assert b'1,200,000' in response.content

    def test_search_by_keyword(self, client, make_job):
        make_job(title='Python Developer')
        make_job(title='Graphic Designer', company_name='Zeta')
        response = client.get(reverse('job_list'), {'q': 'designer'})
        titles = [j.title for j in response.context['all_jobs']]
        assert titles == ['Graphic Designer']

    def test_search_matches_company_name(self, client, make_job):
        make_job(company_name='Zeta Labs')
        make_job(company_name='Acme')
        response = client.get(reverse('job_list'), {'q': 'zeta'})
        assert response.context['paginator'].count == 1

    def test_filter_by_location(self, client, make_job):
        make_job(location='Pune')
        make_job(location='Delhi')
        response = client.get(reverse('job_list'), {'location': 'del'})
        assert [j.location for j in response.context['all_jobs']] == ['Delhi']

    def test_no_results_shows_empty_state(self, client, job):
        response = client.get(reverse('job_list'), {'q': 'nothing-matches'})
        assert b'No jobs found' in response.content

    def test_paginates_ten_per_page(self, client, make_job):
        for i in range(12):
            make_job(title=f'Job {i}')
        first = client.get(reverse('job_list'))
        second = client.get(reverse('job_list'), {'page': 2})
        assert len(first.context['all_jobs']) == 10
        assert len(second.context['all_jobs']) == 2


class TestJobDetail:
    def test_anonymous_sees_login_prompt(self, client, job):
        response = client.get(reverse('job_detail', args=[job.pk]))
        assert response.status_code == 200
        assert b'Log in to apply' in response.content

    def test_seeker_sees_apply_button(self, login, seeker, job):
        response = login(seeker).get(reverse('job_detail', args=[job.pk]))
        assert b'Apply now' in response.content
        assert response.context['application'] is None

    def test_seeker_who_applied_sees_status(self, login, seeker, application):
        response = login(seeker).get(reverse('job_detail', args=[application.job.pk]))
        assert response.context['application'] == application
        assert b'status-applied' in response.content

    def test_owner_sees_applicant_count(self, login, employer, application):
        response = login(employer).get(reverse('job_detail', args=[application.job.pk]))
        assert response.context['applicant_count'] == 1
        assert b'View 1 applicant' in response.content

    def test_missing_job_returns_404(self, client):
        assert client.get(reverse('job_detail', args=[999])).status_code == 404


class TestJobCreateAndUpdate:
    form_data = {
        'title': 'Backend Engineer',
        'company_name': 'Acme',
        'description': 'APIs all day.',
        'location': 'Remote',
        'salary': '900000',
    }

    def test_employer_can_post_job(self, login, employer):
        response = login(employer).post(reverse('job_create'), self.form_data)
        assert response.status_code == 302
        assert response.url == reverse('my_jobs')
        job = Job.objects.get()
        assert job.posted_by == employer
        assert job.title == 'Backend Engineer'

    def test_invalid_job_form_shows_errors(self, login, employer):
        response = login(employer).post(reverse('job_create'), {'title': ''})
        assert response.status_code == 200
        assert response.context['form'].errors
        assert not Job.objects.exists()

    def test_employer_can_edit_own_job(self, login, employer, job):
        data = {**self.form_data, 'title': 'Senior Python Developer'}
        response = login(employer).post(reverse('job_update', args=[job.pk]), data)
        assert response.status_code == 302
        job.refresh_from_db()
        assert job.title == 'Senior Python Developer'

    def test_employer_cannot_edit_someone_elses_job(self, login, other_employer, job):
        response = login(other_employer).post(reverse('job_update', args=[job.pk]), self.form_data)
        assert response.status_code == 404
        job.refresh_from_db()
        assert job.title == 'Python Developer'


class TestMyJobs:
    def test_shows_only_own_jobs_with_counts(self, login, employer, other_employer, make_job, application):
        make_job(title='Not mine', posted_by=other_employer)
        response = login(employer).get(reverse('my_jobs'))
        jobs = list(response.context['my_jobs'])
        assert [j.title for j in jobs] == ['Python Developer']
        assert jobs[0].applicant_count == 1
        assert jobs[0].new_count == 1
