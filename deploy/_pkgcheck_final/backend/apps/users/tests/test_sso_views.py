from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.users.models import UserProfile
from apps.users.services.user_provisioning import DEFAULT_GROUP_NAME


@override_settings(
    SSO_ENABLED=True,
    SSO_CLIENT_ID='demo-client',
    SSO_CLIENT_SECRET='demo-secret',
    SSO_AUTHORIZE_URL='https://sso.example.com/auth',
    SSO_TOKEN_URL='https://sso.example.com/token',
    SSO_USERINFO_URL='https://sso.example.com/userinfo',
    SSO_INTROSPECT_URL='https://sso.example.com/introspect',
    SSO_REDIRECT_URI='https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/',
    SSO_SCOPE='openid email profile custom_scope',
    SSO_KC_IDP_HINT='wechat-work',
    SSO_STATE_TTL_SECONDS=300,
    APP_EXTERNAL_BASE_URL='https://yxcf-yzyy.ynzy-tobacco.com/zszngl',
)
class SsoViewTests(TestCase):
    def test_sso_login_redirects_to_authorize_url(self):
        response = self.client.get('/api/users/sso/login/?next=/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('https://sso.example.com/auth', response['Location'])
        self.assertIn('kc_idp_hint=wechat-work', response['Location'])
        self.assertIn('nonce=', response['Location'])
        self.assertIn('scope=openid+email+profile+custom_scope', response['Location'])

    @override_settings(SSO_ENABLED=False)
    def test_sso_login_disabled_redirects_with_error(self):
        response = self.client.get('/api/users/sso/login/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'https://yxcf-yzyy.ynzy-tobacco.com/zszngl/login?sso_error=disabled',
        )

    def test_callback_rejects_invalid_state(self):
        response = self.client.get('/api/users/sso/callback/?code=ok&state=bad-state')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'https://yxcf-yzyy.ynzy-tobacco.com/zszngl/login?sso_error=state_invalid',
        )

    def test_callback_rejects_missing_code(self):
        session = self.client.session
        session['sso_login_states'] = {'ok-state': {'created_at': 9999999999, 'next_path': '/dashboard'}}
        session.save()
        response = self.client.get('/api/users/sso/callback/?state=ok-state')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'https://yxcf-yzyy.ynzy-tobacco.com/zszngl/login?sso_error=code_missing',
        )

    @patch('apps.users.views.introspect_access_token')
    @patch('apps.users.views.fetch_userinfo')
    @patch('apps.users.views.exchange_code_for_token')
    def test_callback_logs_in_existing_user(self, mock_exchange, mock_userinfo, mock_introspect):
        user = User.objects.create(username='E3003', first_name='wangwu')
        UserProfile.objects.create(user=user, employee_id='E3003')
        session = self.client.session
        session['sso_login_states'] = {'ok-state': {'created_at': 9999999999, 'next_path': '/dashboard'}}
        session.save()
        mock_exchange.return_value = {'access_token': 'abc'}
        mock_introspect.return_value = {'active': True}
        mock_userinfo.return_value = {
            'user_id': 'E3003',
            'name': 'wangwu',
            'preferred_username': '06001569',
        }
        response = self.client.get('/api/users/sso/callback/?code=ok&state=ok-state')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://yxcf-yzyy.ynzy-tobacco.com/zszngl/dashboard')

    @patch('apps.users.views.introspect_access_token')
    @patch('apps.users.views.fetch_userinfo')
    @patch('apps.users.views.exchange_code_for_token')
    def test_callback_auto_creates_user(self, mock_exchange, mock_userinfo, mock_introspect):
        mock_exchange.return_value = {'access_token': 'abc'}
        mock_introspect.return_value = {'active': True}
        mock_userinfo.return_value = {
            'user_id': 'E9999',
            'name': 'new-user',
            'preferred_username': 'E9999',
        }
        session = self.client.session
        session['sso_login_states'] = {'new-state': {'created_at': 9999999999, 'next_path': '/dashboard'}}
        session.save()
        response = self.client.get('/api/users/sso/callback/?code=ok&state=new-state')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://yxcf-yzyy.ynzy-tobacco.com/zszngl/dashboard')
        user = User.objects.get(username='E9999')
        self.assertEqual(user.first_name, 'new-user')
        self.assertFalse(user.has_usable_password())
        self.assertTrue(user.groups.filter(name=DEFAULT_GROUP_NAME).exists())

    @patch('apps.users.views.introspect_access_token')
    @patch('apps.users.views.fetch_userinfo')
    @patch('apps.users.views.exchange_code_for_token')
    def test_callback_rejects_disabled_user(self, mock_exchange, mock_userinfo, mock_introspect):
        user = User.objects.create(username='E4004', first_name='disabled', is_active=False)
        UserProfile.objects.create(user=user, employee_id='E4004')
        mock_exchange.return_value = {'access_token': 'abc'}
        mock_introspect.return_value = {'active': True}
        mock_userinfo.return_value = {
            'user_id': 'E4004',
            'name': 'disabled',
            'preferred_username': 'E4004',
        }
        session = self.client.session
        session['sso_login_states'] = {'dis-state': {'created_at': 9999999999, 'next_path': '/dashboard'}}
        session.save()
        response = self.client.get('/api/users/sso/callback/?code=ok&state=dis-state')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'https://yxcf-yzyy.ynzy-tobacco.com/zszngl/login?sso_error=account_disabled',
        )

    @patch('apps.users.views.introspect_access_token')
    @patch('apps.users.views.fetch_userinfo')
    @patch('apps.users.views.exchange_code_for_token')
    def test_callback_rejects_missing_employee_id(self, mock_exchange, mock_userinfo, mock_introspect):
        mock_exchange.return_value = {'access_token': 'abc'}
        mock_introspect.return_value = {'active': True}
        mock_userinfo.return_value = {
            'name': 'no-employee-id',
            'preferred_username': 'noeid',
        }
        session = self.client.session
        session['sso_login_states'] = {'no-eid': {'created_at': 9999999999, 'next_path': '/dashboard'}}
        session.save()
        response = self.client.get('/api/users/sso/callback/?code=ok&state=no-eid')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'https://yxcf-yzyy.ynzy-tobacco.com/zszngl/login?sso_error=employee_id_missing',
        )

    @patch('apps.users.views.introspect_access_token')
    @patch('apps.users.views.exchange_code_for_token')
    def test_callback_rejects_inactive_token(self, mock_exchange, mock_introspect):
        mock_exchange.return_value = {'access_token': 'abc'}
        mock_introspect.return_value = {'active': False}
        session = self.client.session
        session['sso_login_states'] = {'inactive-state': {'created_at': 9999999999, 'next_path': '/dashboard'}}
        session.save()
        response = self.client.get('/api/users/sso/callback/?code=ok&state=inactive-state')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'https://yxcf-yzyy.ynzy-tobacco.com/zszngl/login?sso_error=token_exchange_failed',
        )

    def test_callback_rejects_open_redirect_next(self):
        response = self.client.get('/api/users/sso/login/?next=https://evil.com/steal')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.com', response['Location'])


class SsoSettingsTests(TestCase):
    def test_secure_proxy_header_is_configured(self):
        from django.conf import settings

        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER, ('HTTP_X_FORWARDED_PROTO', 'https'))
