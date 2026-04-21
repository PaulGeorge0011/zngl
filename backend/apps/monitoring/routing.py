from urllib.parse import urlsplit

from django.conf import settings
from django.urls import path
from .consumers import MonitoringConsumer


def _external_base_path() -> str:
    external_base = (getattr(settings, 'APP_EXTERNAL_BASE_URL', '') or '').strip()
    if not external_base:
        return ''
    return urlsplit(external_base).path.strip('/')


websocket_urlpatterns = [path('ws/monitoring/', MonitoringConsumer.as_asgi())]

_base_path = _external_base_path()
if _base_path:
    websocket_urlpatterns.append(path(f'{_base_path}/ws/monitoring/', MonitoringConsumer.as_asgi()))
