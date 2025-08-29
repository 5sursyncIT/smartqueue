# apps/business/admin.py
"""
Administration Django unifiée pour Business
"""

from django.contrib import admin
from .models import Organization, Service

# Import admin des apps originales pour réutiliser
try:
    # Copier la configuration admin existante
    from apps.organizations.admin import OrganizationAdmin
    from apps.services.admin import ServiceAdmin
    
    # Enregistrer avec la nouvelle app
    admin.site.register(Organization, OrganizationAdmin)
    admin.site.register(Service, ServiceAdmin)
    
except ImportError:
    # Configuration basique si les admins originaux n'existent pas
    @admin.register(Organization)
    class OrganizationAdmin(admin.ModelAdmin):
        list_display = ['name', 'type', 'city', 'region', 'status', 'created_at']
        list_filter = ['type', 'region', 'status']
        search_fields = ['name', 'trade_name', 'city']
    
    @admin.register(Service)
    class ServiceAdmin(admin.ModelAdmin):
        list_display = ['name', 'organization', 'category', 'status', 'created_at']
        list_filter = ['category', 'status']
        search_fields = ['name', 'description']