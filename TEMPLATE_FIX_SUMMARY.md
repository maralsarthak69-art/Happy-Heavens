# Django Template Error Fix

## Problem
The website was showing a 500 error with the message:
```
TemplateSyntaxError: 'block' tag with name 'seo' appears more than once
```

## Root Cause
In `templates/base.html` line 9, there was a Django template tag inside an HTML comment:
```html
<!-- ── SEO: overridable per page via {% block seo %} ─────────────────── -->
```

Even though it was in a comment, Django's template parser was still processing `{% block seo %}` as an actual block declaration, causing a conflict with the real seo block on line 10.

## Fix Applied
Changed the comment to remove the Django template syntax:
```html
<!-- ── SEO: overridable per page via block seo ─────────────────── -->
```

## Additional Improvements
1. Added cache clearing to the build script (`build.sh`)
2. Created a Django management command to clear cache: `python manage.py clear_cache`
3. Created template validation script (`validate_templates.py`)

## Next Steps for Production
The production server needs to:
1. **Restart the Django application** to pick up the template changes
2. **Clear the Django cache** using: `python manage.py clear_cache`
3. Or trigger a **new deployment** to ensure all changes are applied

## Verification
All templates now pass validation with balanced blocks and no duplicate seo blocks.