#!/usr/bin/env python
"""
Simple script to clear Django cache and restart the server.
Run this on the production server to clear template cache.
"""
import os
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    # Clear cache
    from django.core.cache import cache
    cache.clear()
    print("✅ Django cache cleared")
    
    # Also try to clear template cache if it exists
    try:
        from django.template.loader import get_template
        from django.template.engine import Engine
        
        # Clear template cache for all engines
        for engine in Engine.get_default().engine.engines:
            if hasattr(engine, 'env') and hasattr(engine.env, 'cache'):
                engine.env.cache.clear()
        print("✅ Template cache cleared")
    except Exception as e:
        print(f"⚠️  Could not clear template cache: {e}")
    
    print("🔄 Please restart your Django server now")