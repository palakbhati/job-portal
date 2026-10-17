from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from jobs.models import Application, Job
from jobs.validators import validate_file_size


def test_job_str(job):
    assert str(job) == 'Python Developer'


def test_jobs_ordered_newest_first(make_job):
    old = make_job(title='Old')
    new = make_job(title='New')
    Job.objects.filter(pk=old.pk).update(date_posted=date(2020, 1, 1))
    assert list(Job.objects.all()) == [new, old]


def test_application_defaults_to_applied(application):
    assert application.status == Application.STATUS_APPLIED
    assert str(application) == 'seeker applied to Python Developer'


def test_application_is_unique_per_job_and_applicant(application, resume_file):
    with pytest.raises(IntegrityError):
        Application.objects.create(
            job=application.job, applicant=application.applicant, resume=resume_file()
        )


def test_resume_saved_under_resumes_folder(application):
    assert application.resume.name.startswith('resumes/')
    assert application.resume.name.endswith('.pdf')


@pytest.mark.parametrize('name', ['cv.pdf', 'cv.doc', 'cv.docx'])
def test_resume_accepts_allowed_extensions(job, seeker, resume_file, name):
    app = Application(job=job, applicant=seeker, resume=resume_file(name))
    app.full_clean()


@pytest.mark.parametrize('name', ['cv.exe', 'cv.txt', 'cv.png'])
def test_resume_rejects_other_extensions(job, seeker, resume_file, name):
    app = Application(job=job, applicant=seeker, resume=resume_file(name))
    with pytest.raises(ValidationError):
        app.full_clean()


def test_validate_file_size_rejects_large_files(resume_file):
    with pytest.raises(ValidationError, match='File too large'):
        validate_file_size(resume_file(size=5 * 1024 * 1024 + 1))


def test_validate_file_size_accepts_small_files(resume_file):
    validate_file_size(resume_file(size=1024))
