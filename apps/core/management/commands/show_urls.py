from django.core.management.base import BaseCommand
from django.urls import get_resolver

class Command(BaseCommand):
    help = 'Afficher toutes les URLs disponibles'

    def handle(self, *args, **options):
        """Afficher toutes les URLs du projet"""
        self.stdout.write("🔗 URLs disponibles dans SmartQueue Backend:")
        self.stdout.write("=" * 60)
        
        urls = []
        
        def collect_urls(urlpatterns, prefix=''):
            for pattern in urlpatterns:
                if hasattr(pattern, 'pattern'):
                    url = prefix + str(pattern.pattern)
                    if hasattr(pattern, 'callback'):
                        view_name = pattern.callback.__name__ if hasattr(pattern.callback, '__name__') else str(pattern.callback)
                        urls.append((url, view_name))
                    elif hasattr(pattern, 'url_patterns'):
                        collect_urls(pattern.url_patterns, prefix + str(pattern.pattern))
        
        resolver = get_resolver()
        collect_urls(resolver.url_patterns)
        
        # Trier par URL
        urls.sort()
        
        for url, view_name in urls:
            # Nettoyer l'URL pour l'affichage
            clean_url = url.replace('^', '').replace('$', '').replace('\\', '')
            if clean_url.startswith('(?P'):
                # Simplifier les patterns de capture
                clean_url = clean_url.replace('(?P<', '<').replace('>[^/]+)', '>')
            
            self.stdout.write(f"  {clean_url:<40} -> {view_name}")