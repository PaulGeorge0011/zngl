import importlib

from django.test import SimpleTestCase, override_settings


class MonitoringRoutingTests(SimpleTestCase):
    @override_settings(APP_EXTERNAL_BASE_URL='https://yxcf-yzyy.ynzy-tobacco.com/zszngl')
    def test_websocket_routes_include_external_base_prefix(self):
        routing = importlib.import_module('apps.monitoring.routing')
        routing = importlib.reload(routing)
        routes = {pattern.pattern._route for pattern in routing.websocket_urlpatterns}

        self.assertIn('ws/monitoring/', routes)
        self.assertIn('zszngl/ws/monitoring/', routes)
