import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from jobs.models import Application, Job

PASSWORD = 'test-pass-123'


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Keep uploaded test files out of the project's media folder."""
    settings.MEDIA_ROOT = tmp_path / 'media'


@pytest.fixture
def make_user(db):
    def _make_user(username, role='seeker', **extra):
        return get_user_model().objects.create_user(
            username=username, password=PASSWORD, role=role, **extra
        )
    return _make_user


@pytest.fixture
def employer(make_user):
    return make_user('employer', role='employer', email='employer@example.com')


@pytest.fixture
def other_employer(make_user):
    return make_user('other_employer', role='employer')


@pytest.fixture
def seeker(make_user):
    return make_user('seeker', role='seeker', email='seeker@example.com')


@pytest.fixture
def other_seeker(make_user):
    return make_user('other_seeker', role='seeker')


@pytest.fixture
def make_job(employer):
    def _make_job(**overrides):
        data = {
            'title': 'Python Developer',
            'company_name': 'Acme',
            'description': 'Build things.',
            'location': 'Pune',
            'salary': 1200000,
            'posted_by': employer,
        }
        data.update(overrides)
        return Job.objects.create(**data)
    return _make_job


@pytest.fixture
def job(make_job):
    return make_job()


@pytest.fixture
def resume_file():
    def _resume_file(name='resume.pdf', size=1024):
        return SimpleUploadedFile(name, b'%PDF' + b'x' * size, content_type='application/pdf')
    return _resume_file


@pytest.fixture
def application(job, seeker, resume_file):
    return Application.objects.create(
        job=job, applicant=seeker, resume=resume_file(), cover_letter='I would love to join.'
    )


@pytest.fixture
def login(client):
    """Log the test client in as the given user and return it."""
    def _login(user):
        client.login(username=user.username, password=PASSWORD)
        return client
    return _login
