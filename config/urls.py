"""
Configuration URLs principale SmartQueue Sénégal
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Administration Django
    path('admin/', admin.site.urls),
    
    # APIs principales
    path('', include('apps.organizations.urls')),
    path('', include('apps.services.urls')),
    path('', include('apps.queues.urls')),
    path('', include('apps.tickets.urls')),
    path('api/auth/', include('apps.accounts.urls')),  # APIs d'authentification
    path('api/', include('apps.appointments.urls')),   # APIs de rendez-vous
    path('api/', include('apps.notifications.urls')),  # APIs de notifications
    path('api/payments/', include('apps.payments.urls')),  # APIs de paiements
    path('api/analytics/', include('apps.analytics.urls')),  # APIs d'analytics
    
    # Documentation API automatique (Swagger)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Servir les fichiers media en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


