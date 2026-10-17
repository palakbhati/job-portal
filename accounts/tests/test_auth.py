import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from conftest import PASSWORD

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_role_helpers(employer, seeker):
    assert employer.is_employer and not employer.is_seeker
    assert seeker.is_seeker and not seeker.is_employer
    assert str(seeker) == 'seeker'


def test_new_users_default_to_seeker():
    user = User.objects.create_user(username='new', password=PASSWORD)
    assert user.role == 'seeker'


class TestSignup:
    def test_page_loads(self, client):
        assert client.get(reverse('signup')).status_code == 200

    @pytest.mark.parametrize('role', ['employer', 'seeker'])
    def test_signup_creates_user_and_logs_in(self, client, role):
        response = client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'role': role,
            'password1': 'Str0ng-pass!word',
            'password2': 'Str0ng-pass!word',
        })
        assert response.status_code == 302
        assert response.url == reverse('job_list')
        user = User.objects.get(username='newuser')
        assert user.role == role
        assert int(client.session['_auth_user_id']) == user.pk

    def test_mismatched_passwords_show_error(self, client):
        response = client.post(reverse('signup'), {
            'username': 'newuser', 'role': 'seeker',
            'password1': 'Str0ng-pass!word', 'password2': 'different',
        })
        assert response.status_code == 200
        assert b'errorlist' in response.content
        assert not User.objects.filter(username='newuser').exists()


class TestLoginLogout:
    def test_login_redirects_to_job_list(self, client, seeker):
        response = client.post(reverse('login'), {'username': 'seeker', 'password': PASSWORD})
        assert response.url == reverse('job_list')

    def test_login_honours_next(self, client, seeker):
        response = client.post(
            reverse('login'),
            {'username': 'seeker', 'password': PASSWORD, 'next': reverse('my_applications')},
        )
        assert response.url == reverse('my_applications')

    def test_wrong_password_shows_error(self, client, seeker):
        response = client.post(reverse('login'), {'username': 'seeker', 'password': 'wrong'})
        assert response.status_code == 200
        assert b'errorlist' in response.content

    def test_logout_requires_post_and_logs_out(self, login, seeker):
        client = login(seeker)
        assert client.get(reverse('logout')).status_code == 405
        response = client.post(reverse('logout'))
        assert response.url == reverse('job_list')
        assert '_auth_user_id' not in client.session
