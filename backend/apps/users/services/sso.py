from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlsplit, urlunsplit

import requests
from django.conf import settings

SESSION_KEY = 'sso_login_states'


@dataclass(frozen=True)
class SsoUserInfo:
    employee_id: str
    display_name: str
    username: str
    raw: dict[str, Any]
    phone: str = ''


def _normalize_sso_endpoint_url(url: str) -> str:
    raw_url = (url or '').strip()
    if not raw_url:
        return raw_url

    app_external_base = (getattr(settings, 'APP_EXTERNAL_BASE_URL', '') or '').strip()
    if not app_external_base:
        return raw_url

    endpoint_parts = urlsplit(raw_url)
    app_parts = urlsplit(app_external_base)
    if (
        not endpoint_parts.scheme
        or not endpoint_parts.netloc
        or endpoint_parts.scheme != app_parts.scheme
        or endpoint_parts.netloc != app_parts.netloc
    ):
        return raw_url

    app_base_path = app_parts.path.rstrip('/')
    endpoint_path = endpoint_parts.path or ''
    if not app_base_path or not endpoint_path.startswith(f'{app_base_path}/'):
        return raw_url

    normalized_path = endpoint_path[len(app_base_path):] or '/'
    return urlunsplit((
        endpoint_parts.scheme,
        endpoint_parts.netloc,
        normalized_path,
        endpoint_parts.query,
        endpoint_parts.fragment,
    ))


def _get_state_store(session: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    store = session.get(SESSION_KEY)
    if not isinstance(store, dict):
        store = {}
        session[SESSION_KEY] = store
    return store


def prune_login_states(session: Dict[str, Any]) -> None:
    store = _get_state_store(session)
    now = int(time.time())
    ttl = getattr(settings, 'SSO_STATE_TTL_SECONDS', 300)
    expired = [key for key, value in store.items() if now - int(value.get('created_at', 0)) > ttl]
    for key in expired:
        store.pop(key, None)
    session[SESSION_KEY] = store
    if hasattr(session, 'modified'):
        session.modified = True


def register_login_state(
    session: Dict[str, Any],
    next_path: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> str:
    prune_login_states(session)
    store = _get_state_store(session)
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    store[state] = {
        'created_at': int(time.time()),
        'next_path': next_path or '/dashboard',
        'nonce': nonce,
        'redirect_uri': redirect_uri or settings.SSO_REDIRECT_URI,
        'consumed': False,
    }
    session[SESSION_KEY] = store
    if hasattr(session, 'modified'):
        session.modified = True
    return state


def consume_login_state(session: Dict[str, Any], state: str) -> Optional[Dict[str, Any]]:
    prune_login_states(session)
    store = _get_state_store(session)
    payload = store.pop(state, None)
    session[SESSION_KEY] = store
    if hasattr(session, 'modified'):
        session.modified = True
    if not payload or payload.get('consumed'):
        return None
    payload['consumed'] = True
    return payload


def build_authorize_url(
    state: str,
    nonce: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> str:
    params = {
        'client_id': settings.SSO_CLIENT_ID,
        'redirect_uri': redirect_uri or settings.SSO_REDIRECT_URI,
        'response_type': 'code',
        'scope': settings.SSO_SCOPE,
        'state': state,
    }
    if nonce:
        params['nonce'] = nonce

    kc_idp_hint = getattr(settings, 'SSO_KC_IDP_HINT', '').strip()
    if kc_idp_hint:
        params['kc_idp_hint'] = kc_idp_hint

    authorize_url = _normalize_sso_endpoint_url(settings.SSO_AUTHORIZE_URL)
    return f"{authorize_url}?{urlencode(params)}"


def exchange_code_for_token(code: str, redirect_uri: Optional[str] = None) -> dict[str, Any]:
    response = requests.post(
        _normalize_sso_endpoint_url(settings.SSO_TOKEN_URL),
        data={
            'grant_type': 'authorization_code',
            'client_id': settings.SSO_CLIENT_ID,
            'client_secret': settings.SSO_CLIENT_SECRET,
            'code': code,
            'redirect_uri': redirect_uri or settings.SSO_REDIRECT_URI,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def fetch_userinfo(access_token: str) -> dict[str, Any]:
    response = requests.post(
        _normalize_sso_endpoint_url(settings.SSO_USERINFO_URL),
        data={'access_token': access_token},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _normalize_audience(aud: Any) -> list[str]:
    if isinstance(aud, str):
        return [aud]
    if isinstance(aud, list):
        return [str(item) for item in aud]
    return []


def validate_token_claims(claims: dict[str, Any], *, expected_issuer: str, expected_audience: str) -> None:
    issuer = claims.get('iss')
    if expected_issuer and issuer != expected_issuer:
        raise ValueError('iss')

    audiences = _normalize_audience(claims.get('aud'))
    if expected_audience and expected_audience not in audiences:
        raise ValueError('aud')

    exp = claims.get('exp')
    if exp is None or int(exp) <= int(time.time()):
        raise ValueError('exp')


def introspect_access_token(access_token: str) -> dict[str, Any]:
    response = requests.post(
        _normalize_sso_endpoint_url(settings.SSO_INTROSPECT_URL),
        data={
            'token': access_token,
            'client_id': settings.SSO_CLIENT_ID,
            'client_secret': settings.SSO_CLIENT_SECRET,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def normalize_userinfo(payload: dict[str, Any]) -> SsoUserInfo:
    employee_id = (payload.get('user_id') or '').strip()
    if not employee_id:
        raise ValueError('employee_id')

    display_name = (payload.get('name') or '').strip()
    if not display_name:
        family_name = (payload.get('family_name') or '').strip()
        given_name = (payload.get('given_name') or '').strip()
        display_name = f'{family_name}{given_name}'.strip()
    if not display_name:
        display_name = employee_id

    username = (payload.get('preferred_username') or employee_id).strip() or employee_id
    phone = (payload.get('phone') or '').strip()

    return SsoUserInfo(
        employee_id=employee_id,
        display_name=display_name,
        username=username,
        phone=phone,
        raw=payload,
    )
