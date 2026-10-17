"""Role-based access: who can open which page."""
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

EMPLOYER_ONLY = ['job_create', 'my_jobs']
SEEKER_ONLY = ['my_applications']


@pytest.mark.parametrize('url_name', EMPLOYER_ONLY + SEEKER_ONLY)
def test_anonymous_users_redirected_to_login(client, url_name):
    response = client.get(reverse(url_name))
    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={reverse(url_name)}"


@pytest.mark.parametrize('url_name', EMPLOYER_ONLY)
def test_seekers_blocked_from_employer_pages(login, seeker, url_name):
    response = login(seeker).get(reverse(url_name), follow=True)
    assert response.redirect_chain == [(reverse('job_list'), 302)]
    assert b'Only employer accounts' in response.content


@pytest.mark.parametrize('url_name', SEEKER_ONLY)
def test_employers_blocked_from_seeker_pages(login, employer, url_name):
    response = login(employer).get(reverse(url_name), follow=True)
    assert response.redirect_chain == [(reverse('job_list'), 302)]
    assert b'Only job seeker accounts' in response.content


def test_seekers_blocked_from_editing_and_applicants(login, seeker, job):
    client = login(seeker)
    for url in [reverse('job_update', args=[job.pk]), reverse('job_applicants', args=[job.pk])]:
        assert client.get(url).url == reverse('job_list')


def test_employers_cannot_apply(login, employer, job):
    response = login(employer).get(reverse('apply_to_job', args=[job.pk]))
    assert response.url == reverse('job_list')


def test_seekers_cannot_update_status(login, seeker, application):
    response = login(seeker).post(
        reverse('update_application_status', args=[application.pk]), {'status': 'hired'}
    )
    assert response.url == reverse('job_list')
    application.refresh_from_db()
    assert application.status == 'applied'


def test_nav_shows_employer_links(login, employer):
    content = login(employer).get(reverse('job_list')).content
    assert b'Post a Job' in content
    assert b'My Applications' not in content


def test_nav_shows_seeker_links(login, seeker):
    content = login(seeker).get(reverse('job_list')).content
    assert b'My Applications' in content
    assert b'Post a Job' not in content
