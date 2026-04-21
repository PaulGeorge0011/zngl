# 云南中烟单点登录 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留现有本地用户名密码登录的前提下，为制丝智能管理系统新增“云南中烟登录”入口，基于后端主导的 OIDC 授权码流程建立 Django Session，并兼容 `https://yxcf-yzyy.ynzy-tobacco.com/zszngl/` 子路径部署。

**Architecture:** 后端新增 SSO 服务层，负责 state 管理、code 换 token、用户信息解析、按工号匹配/自动建本地账号，并最终通过 Django `login()` 建立现有 session。前端仅在登录页新增第二登录入口，并补齐子路径部署所需的 app base / API base 处理，继续沿用 `usersApi.me()` 恢复登录态。

**Tech Stack:** Django 4.2, DRF SessionAuthentication, requests, Vue 3, TypeScript, Pinia, Vite, nginx reverse proxy

---

## File Structure

### Existing files to modify

- `backend/config/settings/base.py`
  - 新增 SSO 相关环境变量读取、反向代理感知配置、回调/域名配置项，并避免破坏当前 HTTP 离线部署。
- `backend/apps/users/views.py`
  - 新增 `sso_login_view` / `sso_callback_view`，保留现有本地登录逻辑。
- `backend/apps/users/urls.py`
  - 注册 `/sso/login/`、`/sso/callback/`。
- `backend/.env.example`
  - 增加 SSO 配置占位项与生产域名说明，不写入真实 secret。
- `frontend/src/views/login/LoginView.vue`
  - 增加“云南中烟登录”按钮和 SSO 错误提示。
- `frontend/src/router/index.ts`
  - 为 `createWebHistory()` 增加可配置 base，确保 `/zszngl/` 子路径路由可用。
- `frontend/src/api/http.ts`
  - 调整 API base 解析逻辑，避免在子路径部署时把请求发到根路径 `/api/...`。
- `frontend/vite.config.ts`
  - 使用可配置 `base` 构建前端静态资源路径。
- `frontend/.env.production`
  - 增加生产环境 `VITE_APP_BASE` / `VITE_API_BASE` / `VITE_WS_BASE` 示例值。
- `deploy/install.sh`
  - 不写入真实 SSO 密钥；补充 SSO 配置占位、外部 HTTPS 域名/CORS/CSRF 说明，并明确保留服务器上已存在的手工 SSO 配置不被重复部署覆盖。
- `deploy/QUICKSTART.md`
  - 增加云南中烟登录部署配置与回调地址登记说明。

### New files to create

- `backend/apps/users/services/__init__.py`
  - 服务层包声明。
- `backend/apps/users/services/sso.py`
  - OIDC 配置对象、授权 URL 生成、state 存取、token/userinfo 请求、声明校验。
- `backend/apps/users/services/user_provisioning.py`
  - 工号匹配、默认员工组绑定、自动建号逻辑。
- `backend/apps/users/tests/__init__.py`
  - 测试包声明。
- `backend/apps/users/tests/test_sso_services.py`
  - 服务层单元测试。
- `backend/apps/users/tests/test_sso_views.py`
  - 发起登录 / 回调 / 异常分支 / 自动建号集成测试。
- `frontend/src/utils/appBase.ts`
  - 统一解析前端 base path 与 API 登录跳转 URL，减少在组件里散落字符串拼接。

### External configuration values to use during implementation

- 生产访问基址：`https://yxcf-yzyy.ynzy-tobacco.com/zszngl/`
- 推荐回调地址：`https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/`
- `client_id` 已由用户提供，实施时写入服务器 `.env`，不要提交到仓库。
- `client_secret` 已由用户提供，实施时写入服务器 `.env`，不要提交到仓库、计划文件或示例配置。
- SSO 的 `base_url` / authorize / token / userinfo 端点按现有《单点登录集成指南》填写，不要猜测新 URL。

## Chunk 1: Backend SSO foundation

### Task 1: Add backend SSO settings and service skeleton

**Files:**
- Create: `backend/apps/users/services/__init__.py`
- Create: `backend/apps/users/services/sso.py`
- Modify: `backend/config/settings/base.py`
- Modify: `backend/.env.example`
- Test: `backend/apps/users/tests/test_sso_services.py`

- [ ] **Step 1: Write the failing service tests**

Create `backend/apps/users/tests/test_sso_services.py` with focused tests for:

```python
from django.test import SimpleTestCase, override_settings
from apps.users.services.sso import (
    build_authorize_url,
    consume_login_state,
    prune_login_states,
    register_login_state,
    validate_token_claims,
)

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
        SSO_SCOPE='openid profile',
    )
    def test_build_authorize_url_includes_expected_query(self):
        url = build_authorize_url('state-123')
        self.assertIn('client_id=demo-client', url)
        self.assertIn('state=state-123', url)
        self.assertIn('redirect_uri=https%3A%2F%2Fexample.com%2Fzszngl%2Fapi%2Fusers%2Fsso%2Fcallback%2F', url)

    def test_validate_token_claims_rejects_wrong_audience(self):
        claims = {'iss': 'https://issuer.example.com', 'aud': 'other-client', 'exp': 4102444800}
        with self.assertRaisesMessage(ValueError, 'aud'):
            validate_token_claims(claims, expected_issuer='https://issuer.example.com', expected_audience='demo-client')
```

- [ ] **Step 2: Run the backend service tests to confirm they fail**

Run:

```bash
cd backend && python manage.py test apps.users.tests.test_sso_services -v 2
```

Expected: FAIL with import errors because `apps.users.services.sso` and helper functions do not exist yet.

- [ ] **Step 3: Add SSO settings placeholders in Django settings**

In `backend/config/settings/base.py`, add env-backed settings for:

```python
SSO_ENABLED = os.getenv('SSO_ENABLED', 'False').lower() == 'true'
SSO_CLIENT_ID = os.getenv('SSO_CLIENT_ID', '')
SSO_CLIENT_SECRET = os.getenv('SSO_CLIENT_SECRET', '')
SSO_BASE_URL = os.getenv('SSO_BASE_URL', '')
SSO_AUTHORIZE_URL = os.getenv('SSO_AUTHORIZE_URL', '')
SSO_TOKEN_URL = os.getenv('SSO_TOKEN_URL', '')
SSO_USERINFO_URL = os.getenv('SSO_USERINFO_URL', '')
SSO_INTROSPECT_URL = os.getenv('SSO_INTROSPECT_URL', '')
SSO_REDIRECT_URI = os.getenv('SSO_REDIRECT_URI', '')
SSO_SCOPE = os.getenv('SSO_SCOPE', 'openid profile')
SSO_STATE_TTL_SECONDS = int(os.getenv('SSO_STATE_TTL_SECONDS', '300'))
APP_EXTERNAL_BASE_URL = os.getenv('APP_EXTERNAL_BASE_URL', '')
```

Also add reverse-proxy awareness needed for `https://yxcf-yzyy.ynzy-tobacco.com` behind proxy:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

Do **not** unconditionally set:

```python
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
```

because the current offline installer still deploys plain HTTP internally on `http://<ip>:9527`. Instead, add env-backed toggles such as:

```python
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() == 'true'
```

and leave them disabled by default so current deployments do not lose session cookies. Production HTTPS environments can explicitly enable them in server `.env`.

- [ ] **Step 4: Add `.env.example` placeholders without real secrets**

Append placeholder keys to `backend/.env.example`:

```dotenv
APP_EXTERNAL_BASE_URL=https://yxcf-yzyy.ynzy-tobacco.com/zszngl
SSO_ENABLED=False
SSO_CLIENT_ID=
SSO_CLIENT_SECRET=
SSO_BASE_URL=
SSO_AUTHORIZE_URL=
SSO_TOKEN_URL=
SSO_USERINFO_URL=
SSO_INTROSPECT_URL=
SSO_REDIRECT_URI=https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/
SSO_SCOPE=openid profile
SSO_STATE_TTL_SECONDS=300
```

Add a short comment that production secrets must be written manually on the server and never committed.

- [ ] **Step 5: Implement the minimal SSO service layer**

Create `backend/apps/users/services/sso.py` with these units:

```python
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings

SESSION_KEY = 'sso_login_states'

@dataclass(frozen=True)
class SsoUserInfo:
    employee_id: str
    display_name: str
    username: str
    raw: dict[str, Any]


def prune_login_states(session: dict[str, Any]) -> None: ...
def register_login_state(session: dict[str, Any], next_path: str | None = None) -> str: ...
def consume_login_state(session: dict[str, Any], state: str) -> dict[str, Any] | None: ...
def build_authorize_url(state: str) -> str: ...
def exchange_code_for_token(code: str) -> dict[str, Any]: ...
def fetch_userinfo(access_token: str) -> dict[str, Any]: ...
def validate_token_claims(claims: dict[str, Any], *, expected_issuer: str, expected_audience: str) -> None: ...
def normalize_userinfo(payload: dict[str, Any]) -> SsoUserInfo: ...
```

Implementation rules:
- state 存到 session 中的字典结构，支持多个待消费 state。
- 每次注册和消费前先清理过期 state。
- `normalize_userinfo()` 只从文档实际字段映射工号/姓名/登录名，不要硬猜多个字段后静默吞错；若缺工号直接抛 `ValueError('employee_id')`。
- `exchange_code_for_token()` / `fetch_userinfo()` 使用 `requests`, `timeout=10`。
- 不打印 token 明文到日志。

- [ ] **Step 6: Re-run the service tests**

Run:

```bash
cd backend && python manage.py test apps.users.tests.test_sso_services -v 2
```

Expected: PASS for service-level tests.

- [ ] **Step 7: Commit backend foundation changes**

```bash
git add backend/config/settings/base.py backend/.env.example backend/apps/users/services/__init__.py backend/apps/users/services/sso.py backend/apps/users/tests/test_sso_services.py
git commit -m "feat: add SSO service foundation"
```

### Task 2: Add user provisioning for SSO auto-creation

**Files:**
- Create: `backend/apps/users/services/user_provisioning.py`
- Modify: `backend/apps/users/services/sso.py`
- Test: `backend/apps/users/tests/test_sso_services.py`

- [ ] **Step 1: Write the failing provisioning tests**

Extend `backend/apps/users/tests/test_sso_services.py` with DB-backed cases using `TestCase`:

```python
from django.contrib.auth.models import Group, User
from django.test import TestCase
from apps.users.models import UserProfile
from apps.users.services.user_provisioning import provision_user_from_sso
from apps.users.services.sso import SsoUserInfo

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
```

- [ ] **Step 2: Run the provisioning tests to verify they fail**

Run:

```bash
cd backend && python manage.py test apps.users.tests.test_sso_services.UserProvisioningTests -v 2
```

Expected: FAIL because `user_provisioning.py` and `provision_user_from_sso()` do not exist yet.

- [ ] **Step 3: Implement minimal provisioning logic**

Create `backend/apps/users/services/user_provisioning.py`:

```python
from django.contrib.auth.models import Group, User
from django.db import transaction
from apps.users.models import UserProfile
from apps.users.services.sso import SsoUserInfo

DEFAULT_GROUP_NAME = '员工'

@transaction.atomic
def provision_user_from_sso(info: SsoUserInfo) -> User:
    profile = UserProfile.objects.select_related('user').filter(employee_id=info.employee_id).first()
    if profile:
        return profile.user

    username = build_unique_username(info.employee_id)
    user = User(username=username, first_name=info.display_name, is_active=True)
    user.set_unusable_password()
    user.save()

    group, _ = Group.objects.get_or_create(name=DEFAULT_GROUP_NAME)
    user.groups.set([group])
    UserProfile.objects.create(user=user, employee_id=info.employee_id)
    return user
```

Also add `build_unique_username()` with the fallback order:
- exact employee_id
- `ynzy_<employee_id>`
- `ynzy_<employee_id>_<n>`

Do not overwrite role/group for an existing matched user.

- [ ] **Step 4: Re-run provisioning tests**

Run:

```bash
cd backend && python manage.py test apps.users.tests.test_sso_services.UserProvisioningTests -v 2
```

Expected: PASS.

- [ ] **Step 5: Commit provisioning logic**

```bash
git add backend/apps/users/services/user_provisioning.py backend/apps/users/tests/test_sso_services.py
git commit -m "feat: add SSO user provisioning"
```

## Chunk 2: Backend views, routes, and error handling

### Task 3: Add SSO login and callback views

**Files:**
- Modify: `backend/apps/users/views.py`
- Modify: `backend/apps/users/urls.py`
- Modify: `backend/apps/users/services/sso.py`
- Modify: `backend/apps/users/services/user_provisioning.py`
- Test: `backend/apps/users/tests/test_sso_views.py`

- [ ] **Step 1: Write the failing view tests**

Create `backend/apps/users/tests/test_sso_views.py` with these cases:

```python
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from apps.users.models import UserProfile

@override_settings(
    SSO_ENABLED=True,
    SSO_CLIENT_ID='demo-client',
    SSO_CLIENT_SECRET='demo-secret',
    SSO_AUTHORIZE_URL='https://sso.example.com/auth',
    SSO_TOKEN_URL='https://sso.example.com/token',
    SSO_USERINFO_URL='https://sso.example.com/userinfo',
    SSO_REDIRECT_URI='https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/',
)
class SsoViewTests(TestCase):
    def test_sso_login_redirects_to_authorize_url(self):
        response = self.client.get('/api/users/sso/login/?next=/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('https://sso.example.com/auth', response['Location'])

    @patch('apps.users.views.fetch_userinfo')
    @patch('apps.users.views.exchange_code_for_token')
    def test_callback_logs_in_existing_user(self, token_mock, userinfo_mock):
        user = User.objects.create(username='E3003', first_name='王五')
        UserProfile.objects.create(user=user, employee_id='E3003')
        session = self.client.session
        session['sso_login_states'] = {'ok-state': {'created_at': 9999999999, 'next_path': '/dashboard'}}
        session.save()
        token_mock.return_value = {'access_token': 'abc', 'id_token_claims': {'iss': 'https://issuer.example.com', 'aud': 'demo-client', 'exp': 4102444800}}
        userinfo_mock.return_value = {'employee_id': 'E3003', 'display_name': '王五', 'username': 'wangwu'}
        response = self.client.get('/api/users/sso/callback/?code=ok&state=ok-state')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith('/dashboard'))

    def test_callback_rejects_invalid_state(self):
        response = self.client.get('/api/users/sso/callback/?code=ok&state=bad-state')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login?sso_error=state_invalid', response['Location'])
```

- [ ] **Step 2: Run the view tests and confirm they fail**

Run:

```bash
cd backend && python manage.py test apps.users.tests.test_sso_views -v 2
```

Expected: FAIL because the routes and SSO views do not exist.

- [ ] **Step 3: Implement SSO login and callback views**

In `backend/apps/users/views.py`, add:

```python
from django.shortcuts import redirect
from apps.users.services.sso import (
    build_authorize_url,
    consume_login_state,
    exchange_code_for_token,
    fetch_userinfo,
    normalize_userinfo,
    register_login_state,
    validate_token_claims,
)
from apps.users.services.user_provisioning import provision_user_from_sso

@api_view(['GET'])
@permission_classes([AllowAny])
def sso_login_view(request): ...

@api_view(['GET'])
@permission_classes([AllowAny])
def sso_callback_view(request): ...
```

Behavior requirements:
- `SSO_ENABLED=False` 时直接重定向 `/login?sso_error=disabled`
- `next` 只允许站内相对路径，否则丢弃并回 `/dashboard`
- callback 内对 `code` 缺失、state 无效、token/userinfo 失败、工号缺失、账号禁用分别映射到不同 `sso_error`
- 成功后调用现有 Django `login(request, user)`
- 成功登录后复用 `_user_data()` 的本地角色语义，不新增新的前端用户结构

- [ ] **Step 4: Register routes**

Update `backend/apps/users/urls.py` to add:

```python
path('sso/login/', views.sso_login_view, name='users-sso-login'),
path('sso/callback/', views.sso_callback_view, name='users-sso-callback'),
```

Keep the existing `/login/`, `/logout/`, `/me/`, `/manage/` routes unchanged.

- [ ] **Step 5: Re-run the view tests**

Run:

```bash
cd backend && python manage.py test apps.users.tests.test_sso_views -v 2
```

Expected: PASS.

- [ ] **Step 6: Run the full users app test subset**

Run:

```bash
cd backend && python manage.py test apps.users.tests -v 2
```

Expected: PASS for both service and view test modules.

- [ ] **Step 7: Commit SSO views and routes**

```bash
git add backend/apps/users/views.py backend/apps/users/urls.py backend/apps/users/tests/test_sso_views.py backend/apps/users/services/sso.py backend/apps/users/services/user_provisioning.py
git commit -m "feat: add SSO auth endpoints"
```

### Task 4: Harden production settings for HTTPS + proxy deployment

**Files:**
- Modify: `backend/config/settings/base.py`
- Test: `backend/apps/users/tests/test_sso_views.py`

- [ ] **Step 1: Add a failing redirect/security settings test**

Add to `backend/apps/users/tests/test_sso_views.py`:

```python
from django.conf import settings

class SsoSettingsTests(TestCase):
    def test_secure_proxy_header_is_configured(self):
        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER, ('HTTP_X_FORWARDED_PROTO', 'https'))
```

Also add env-toggle coverage to ensure the default remains safe for current HTTP deployment:

```python
@override_settings(DEBUG=False)
class SsoCookieDefaultsTests(SimpleTestCase):
    def test_secure_cookie_flags_are_not_forced_on_without_env(self):
        self.assertFalse(settings.SESSION_COOKIE_SECURE)
        self.assertFalse(settings.CSRF_COOKIE_SECURE)
```

- [ ] **Step 2: Run the specific settings test**

Run:

```bash
cd backend && python manage.py test apps.users.tests.test_sso_views.SsoSettingsTests -v 2
```

Expected: FAIL if secure proxy settings are not yet configured as required.

- [ ] **Step 3: Finish the minimal production hardening**

Ensure `backend/config/settings/base.py` includes or preserves:
- `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`
- env-backed `SESSION_COOKIE_SECURE` toggle defaulting to `False`
- env-backed `CSRF_COOKIE_SECURE` toggle defaulting to `False`
- production examples updated for `CSRF_TRUSTED_ORIGINS=https://yxcf-yzyy.ynzy-tobacco.com`

Do not add broad unrelated security settings; keep only what is needed for this SSO flow and do not break the current HTTP offline deployment.

- [ ] **Step 4: Re-run the backend users tests**

Run:

```bash
cd backend && python manage.py test apps.users.tests -v 2
```

Expected: PASS.

- [ ] **Step 5: Commit the proxy/HTTPS configuration**

```bash
git add backend/config/settings/base.py backend/apps/users/tests/test_sso_views.py backend/.env.example
git commit -m "fix: configure proxy-aware SSO settings"
```

## Chunk 3: Frontend login entry and subpath support

### Task 5: Add frontend base-path helpers for `/zszngl/`

**Files:**
- Create: `frontend/src/utils/appBase.ts`
- Modify: `frontend/src/api/http.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/.env.production`
- Test: `frontend` build as verification command

- [ ] **Step 1: Write a small failing helper-driven change plan in code comments/tests substitute**

Because the current frontend has no unit-test runner configured, use a build-first TDD substitute:
- first introduce `appBase.ts` API contract
- wire imports before implementation
- confirm TypeScript build fails if helpers are missing

Start by modifying `frontend/src/api/http.ts` and `frontend/src/router/index.ts` to import these missing helpers:

```ts
import { getApiBase, getRouterBase } from '@/utils/appBase'
```

Expected temporary build failure until helper file exists.

- [ ] **Step 2: Run the frontend build to verify failure**

Run:

```bash
cd frontend && npm run build
```

Expected: FAIL because `@/utils/appBase` does not exist.

- [ ] **Step 3: Implement `appBase.ts` and wire base usage**

Create `frontend/src/utils/appBase.ts`:

```ts
function normalizeBase(value: string | undefined, fallback = '/'): string {
  const raw = (value || fallback).trim()
  if (!raw || raw === '/') return '/'
  return `/${raw.replace(/^\/+|\/+$/g, '')}/`
}

export function getRouterBase() {
  return normalizeBase(import.meta.env.VITE_APP_BASE, '/')
}

export function getApiBase() {
  const explicit = import.meta.env.VITE_API_BASE?.trim()
  if (explicit) return explicit
  const base = getRouterBase()
  return base === '/' ? '' : base.replace(/\/$/, '')
}

export function buildSsoLoginUrl(next = '/dashboard') {
  const apiBase = getApiBase()
  return `${apiBase}/api/users/sso/login/?next=${encodeURIComponent(next)}`
}
```

Then update:
- `frontend/src/api/http.ts` → `baseURL: getApiBase()`
- `frontend/src/router/index.ts` → `createWebHistory(getRouterBase())`
- `frontend/vite.config.ts` → use Vite's `loadEnv(mode, process.cwd(), '')` and set:

```ts
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    base: env.VITE_APP_BASE || '/',
    // existing config
  }
})
```

- `frontend/.env.production` with:

```dotenv
VITE_APP_BASE=/zszngl/
VITE_API_BASE=/zszngl
VITE_WS_BASE=wss://yxcf-yzyy.ynzy-tobacco.com/zszngl
```

This keeps the app working under the external `/zszngl/` location while internal nginx continues serving root.

- [ ] **Step 4: Re-run the frontend build**

Run:

```bash
cd frontend && npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit base-path support**

```bash
git add frontend/src/utils/appBase.ts frontend/src/api/http.ts frontend/src/router/index.ts frontend/vite.config.ts frontend/.env.production
git commit -m "feat: add frontend base-path support for SSO deployment"
```

### Task 6: Add the “云南中烟登录” entry and login-page error handling

**Files:**
- Modify: `frontend/src/views/login/LoginView.vue`
- Modify: `frontend/src/api/users.ts` (only if helper export is preferable there)
- Modify: `frontend/src/utils/appBase.ts` (if needed)
- Test: `frontend` build as verification command

- [ ] **Step 1: Introduce a failing import/build for SSO login button behavior**

In `frontend/src/views/login/LoginView.vue`, reference these not-yet-wired items:

```ts
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { buildSsoLoginUrl } from '@/utils/appBase'
```

Temporarily add template bindings for:
- `ssoLoginUrl`
- `ssoErrorMessage`

without completing the script logic yet.

- [ ] **Step 2: Run the frontend build to confirm failure**

Run:

```bash
cd frontend && npm run build
```

Expected: FAIL because the login page references missing computed state.

- [ ] **Step 3: Implement the login page changes minimally**

Update `frontend/src/views/login/LoginView.vue` to:
- keep the current username/password flow untouched
- add a second button labeled `云南中烟登录`
- compute `ssoLoginUrl = buildSsoLoginUrl('/dashboard')`
- on click set `window.location.href = ssoLoginUrl`
- read `route.query.sso_error` and map to friendly messages:

```ts
const SSO_ERROR_MESSAGES: Record<string, string> = {
  disabled: '云南中烟登录当前未启用',
  state_invalid: '登录状态已失效，请重新发起登录',
  token_exchange_failed: '统一认证返回异常，请稍后重试',
  userinfo_failed: '未能获取统一认证用户信息',
  employee_id_missing: '统一认证未返回工号，无法完成登录',
  account_disabled: '本系统账号已被禁用，请联系管理员',
}
```

Template changes:
- keep existing primary login button
- add a visual divider such as `— 或 —`
- add secondary button for SSO
- show `el-alert` or lightweight error text when `ssoErrorMessage` exists

- [ ] **Step 4: Re-run the frontend build**

Run:

```bash
cd frontend && npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit the login UI changes**

```bash
git add frontend/src/views/login/LoginView.vue frontend/src/utils/appBase.ts
git commit -m "feat: add Yunnan Tobacco SSO login entry"
```

## Chunk 4: Deployment templates, docs, and end-to-end verification

### Task 7: Preserve SSO config in deployment templates and docs

**Files:**
- Modify: `deploy/install.sh`
- Modify: `deploy/QUICKSTART.md`
- Modify: `backend/.env.example`

- [ ] **Step 1: Add a deployment checklist note before changing scripts**

Open the target files and confirm these requirements are reflected after editing:
- do not embed real `client_secret`
- expose the exact callback URL
- explain that external reverse proxy path is `/zszngl/`
- document trusted origin as `https://yxcf-yzyy.ynzy-tobacco.com`

- [ ] **Step 2: Update `deploy/install.sh` minimally**

Change the deployment flow so that repeat deployments do **not** wipe manually filled SSO secrets.

This requires updates in **two places**, not just the `.env` creation block:

1. **Project sync stage**
   - current `rsync -a --delete` must not delete `backend/.env`
   - update the sync command to exclude the runtime env file, for example:

```bash
rsync -a --delete --exclude 'backend/.env' "${CURRENT_DIR}/" "${PROJECT_DIR}/"
```

2. **Backend install stage**
   - if `${PROJECT_DIR}/backend/.env` does not exist, create it from the installer template
   - if it already exists, preserve it and only print a warning reminding the operator to manually add/update SSO keys
   - do not overwrite existing `.env` with `cat > .env <<EOF` on every run

A valid backend install approach is:

```bash
if [ ! -f .env ]; then
  cat > .env <<'EOF'
  ...default generated content...
EOF
else
  warn "Existing backend/.env detected; preserving it. Update SSO settings manually if needed."
fi
```

Within the template for first-time creation:
- existing generated local values should remain usable for offline deployment
- SSO keys should be included as commented placeholders, e.g.

```dotenv
# APP_EXTERNAL_BASE_URL=https://yxcf-yzyy.ynzy-tobacco.com/zszngl
# SSO_ENABLED=False
# SSO_CLIENT_ID=
# SSO_CLIENT_SECRET=
# SSO_BASE_URL=
# SSO_AUTHORIZE_URL=
# SSO_TOKEN_URL=
# SSO_USERINFO_URL=
# SSO_REDIRECT_URI=https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/
```

Do not inject the real secret into `install.sh`.

- [ ] **Step 3: Update `deploy/QUICKSTART.md`**

Add a short section:
- external access path: `https://yxcf-yzyy.ynzy-tobacco.com/zszngl/`
- SSO callback registration: `https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/`
- production `.env` must manually fill `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, and guide-provided endpoint URLs
- reverse proxy snippet assumption: external `/zszngl/` proxies to internal app server root

- [ ] **Step 4: Review `.env.example` and docs for secret leakage**

Search manually to verify the real `client_secret` was not copied into tracked files.

- [ ] **Step 5: Commit deploy/doc updates**

```bash
git add deploy/install.sh deploy/QUICKSTART.md backend/.env.example
git commit -m "docs: add SSO deployment configuration notes"
```

### Task 8: Run final verification before claiming completion

**Files:**
- Test only: `backend/apps/users/tests/test_sso_services.py`
- Test only: `backend/apps/users/tests/test_sso_views.py`
- Test only: `frontend/src/views/login/LoginView.vue`
- Test only: `frontend/src/utils/appBase.ts`

- [ ] **Step 1: Run backend SSO tests**

Run:

```bash
cd backend && python manage.py test apps.users.tests -v 2
```

Expected: PASS.

- [ ] **Step 2: Run frontend production build**

Run:

```bash
cd frontend && npm run build
```

Expected: PASS.

- [ ] **Step 3: Verify no secret leaked to git diff**

Run:

```bash
git -C "F:/zs2 Management System" diff -- backend/.env.example deploy/install.sh deploy/QUICKSTART.md docs/superpowers/specs/2026-04-03-yunnan-cigarette-sso-design.md
```

Expected: no real `client_secret` present in tracked file diffs.

- [ ] **Step 4: Manual browser verification checklist**

Verify in browser against the deployed domain/path:
- open `https://yxcf-yzyy.ynzy-tobacco.com/zszngl/login`
- confirm local login still renders normally
- confirm `云南中烟登录` button is visible
- click SSO button and confirm browser is redirected to the unified login page
- complete login with a test account whose工号 exists in the response
- confirm callback lands at `/zszngl/api/users/sso/callback/`
- confirm final page is `/zszngl/dashboard`
- confirm page refresh still stays logged in
- confirm logout only exits this system

- [ ] **Step 5: Commit any final verification fixes**

If verification required no code changes, skip this commit.
If a small fix was needed, commit it with a focused message such as:

```bash
git add <exact files>
git commit -m "fix: handle SSO callback edge case"
```

## Plan review notes

- This plan intentionally does **not** commit the real `client_secret` anywhere.
- The exact OIDC endpoint URLs must be copied from the existing HTML integration guide during implementation.
- The callback URL to register with the identity provider should be:
  - `https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/`
- The implementation must remain compatible with the current local login flow and current `usersApi.me()` session restoration.
