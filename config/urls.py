"""
Configuration URLs principale SmartQueue Sénégal
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.core.views import home_view

urlpatterns = [
    # Page d'accueil backend
    path('', home_view, name='home'),
    
    # Administration Django
    path('admin/', admin.site.urls),
    
    # APIs principales (Architecture restructurée - Phase de test)
    path('api/core/', include('apps.core.urls')),              # APIs utilitaires core
    path('api/business/', include('apps.business.urls')),      # APIs business (orgs + services unifiés) ✅
    path('api/queue-management/', include('apps.queue_management.urls')),  # APIs files + tickets unifiés ✅
    path('api/accounts/', include('apps.accounts.urls')),          # APIs d'authentification
    # À réactiver après correction des dépendances (prochaine étape)
    # path('api/locations/', include('apps.locations.urls')),    # APIs géolocalisation intelligente
    # path('api/appointments/', include('apps.appointments.urls')),   # APIs de rendez-vous
    # path('api/notifications/', include('apps.notifications.urls')), # APIs de notifications  
    # path('api/payments/', include('apps.payments.urls')),      # APIs de paiements
    # path('api/analytics/', include('apps.analytics.urls')),    # APIs d'analytics
    
    # Documentation API automatique (Swagger)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Servir les fichiers media en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


