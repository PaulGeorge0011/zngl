from unittest.mock import patch

from django.test import TestCase, override_settings


PROD_APP_BASE = 'https://yxcf-yzyy.ynzy-tobacco.com/zszngl'
PROD_CALLBACK = f'{PROD_APP_BASE}/api/users/sso/callback/'


@override_settings(
    SSO_ENABLED=True,
    ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1', '192.168.1.20'],
    SSO_CLIENT_ID='demo-client',
    SSO_CLIENT_SECRET='demo-secret',
    SSO_AUTHORIZE_URL='https://sso.example.com/auth',
    SSO_TOKEN_URL='https://sso.example.com/token',
    SSO_USERINFO_URL='https://sso.example.com/userinfo',
    SSO_INTROSPECT_URL='https://sso.example.com/introspect',
    SSO_REDIRECT_URI=PROD_CALLBACK,
    SSO_SCOPE='openid email profile custom_scope',
    SSO_KC_IDP_HINT='wechat-work',
    APP_EXTERNAL_BASE_URL=PROD_APP_BASE,
)
class SsoOriginBehaviorTests(TestCase):
    def test_login_on_localhost_uses_request_origin_for_redirect_uri(self):
        response = self.client.get('/api/users/sso/login/?next=/dashboard', HTTP_HOST='localhost:3001')
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            'redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fusers%2Fsso%2Fcallback%2F',
            response['Location'],
        )

    def test_login_on_127_backend_normalizes_redirect_uri_to_localhost(self):
        response = self.client.get('/api/users/sso/login/?next=/dashboard', HTTP_HOST='127.0.0.1:8000')
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            'redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fusers%2Fsso%2Fcallback%2F',
            response['Location'],
        )

    def test_login_rejects_untrustworthy_http_origin(self):
        response = self.client.get('/api/users/sso/login/?next=/dashboard', HTTP_HOST='192.168.1.20:3001')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'{PROD_APP_BASE}/login?sso_error=origin_untrusted')

    @patch('apps.users.views.introspect_access_token')
    @patch('apps.users.views.fetch_userinfo')
    @patch('apps.users.views.exchange_code_for_token')
    def test_callback_on_localhost_redirects_back_to_local_app(self, mock_exchange, mock_userinfo, mock_introspect):
        local_callback = 'http://localhost:8000/api/users/sso/callback/'
        mock_exchange.return_value = {'access_token': 'abc'}
        mock_introspect.return_value = {'active': True}
        mock_userinfo.return_value = {
            'user_id': 'E5005',
            'name': 'local user',
            'preferred_username': 'E5005',
        }
        session = self.client.session
        session['sso_login_states'] = {
            'local-state': {
                'created_at': 9999999999,
                'next_path': '/dashboard',
                'redirect_uri': local_callback,
            }
        }
        session.save()

        response = self.client.get(
            '/api/users/sso/callback/?code=ok&state=local-state',
            HTTP_HOST='localhost:3001',
        )

        mock_exchange.assert_called_once_with('ok', redirect_uri=local_callback)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://localhost:3001/dashboard')
