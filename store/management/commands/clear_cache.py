from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Clear Django cache to fix template issues'

    def handle(self, *args, **options):
        cache.clear()
        self.stdout.write(
            self.style.SUCCESS('✅ Successfully cleared Django cache')
        )
        
        # Also try to clear template loader cache
        try:
            from django.template.loader import get_template
            from django.template import engines
            
            for engine in engines.all():
                if hasattr(engine, 'engine'):
                    engine.engine.get_template.cache_clear()
                    
            self.stdout.write(
                self.style.SUCCESS('✅ Successfully cleared template loader cache')
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️ Could not clear template loader cache: {e}')
            )