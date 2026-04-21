from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib.auth.models import User

from apps.users.models import UserProfile
from apps.users.services.sso import (
    build_authorize_url,
    consume_login_state,
    register_login_state,
    validate_token_claims,
)
from apps.users.services.user_provisioning import provision_user_from_sso
from apps.users.services.sso import SsoUserInfo


class SsoServiceTests(SimpleTestCase):
    def test_register_login_state_keeps_multiple_pending_entries(self):
        session = {}
        state_a = register_login_state(session, next_path='/dashboard')
        state_b = register_login_state(session, next_path='/quality')
        self.assertNotEqual(state_a, state_b)
        self.assertEqual(len(session['sso_login_states']), 2)

    def test_consume_login_state_rejects_unknown_state(self):
        session = {'sso_login_states': {}}
        self.assertIsNone(consume_login_state(session, 'missing'))

    @override_settings(
        SSO_CLIENT_ID='demo-client',
        SSO_REDIRECT_URI='https://example.com/zszngl/api/users/sso/callback/',
        SSO_AUTHORIZE_URL='https://sso.example.com/auth',
        SSO_SCOPE='openid email profile custom_scope',
        SSO_KC_IDP_HINT='wechat-work',
    )
    def test_build_authorize_url_includes_expected_query(self):
        url = build_authorize_url('state-123', nonce='nonce-123')
        self.assertIn('client_id=demo-client', url)
        self.assertIn('state=state-123', url)
        self.assertIn('nonce=nonce-123', url)
        self.assertIn('kc_idp_hint=wechat-work', url)
        self.assertIn('scope=openid+email+profile+custom_scope', url)
        self.assertIn('redirect_uri=https%3A%2F%2Fexample.com%2Fzszngl%2Fapi%2Fusers%2Fsso%2Fcallback%2F', url)

    def test_validate_token_claims_rejects_wrong_audience(self):
        claims = {'iss': 'https://issuer.example.com', 'aud': 'other-client', 'exp': 4102444800}
        with self.assertRaisesMessage(ValueError, 'aud'):
            validate_token_claims(claims, expected_issuer='https://issuer.example.com', expected_audience='demo-client')


class UserProvisioningTests(TestCase):
    def test_provision_existing_user_by_employee_id(self):
        user = User.objects.create(username='E1001', first_name='Old Name')
        UserProfile.objects.create(user=user, employee_id='E1001')
        result = provision_user_from_sso(SsoUserInfo(employee_id='E1001', display_name='New Name', username='old', raw={}))
        self.assertEqual(result.pk, user.pk)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Old Name')

    def test_provision_new_user_creates_worker_group_membership(self):
        user = provision_user_from_sso(SsoUserInfo(employee_id='E2002', display_name='张三', username='zhangsan', raw={}))
        self.assertTrue(user.groups.filter(name='员工').exists())
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.profile.employee_id, 'E2002')
