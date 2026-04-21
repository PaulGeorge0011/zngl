from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('apps.users.urls')),
    path('api/equipment/', include('apps.equipment.urls')),
    path('api/monitoring/', include('apps.monitoring.urls')),
    path('api/ai/', include('apps.ai_analysis.urls')),
    path('api/quality/', include('apps.quality.urls')),
    path('api/safety/', include('apps.safety.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
