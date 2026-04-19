"""
SEO utility views: robots.txt and sitemap.xml
"""
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.utils import timezone

from store.models import Product, Category


@cache_page(60 * 60 * 24)  # cache for 24 hours
def robots_txt(request):
    """Serve robots.txt to guide search engine crawlers."""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "Disallow: /orders/",
        "Disallow: /accounts/",
        "",
        "Sitemap: https://happyheavens.in/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@cache_page(60 * 60 * 6)  # cache for 6 hours
def sitemap_xml(request):
    """Generate a basic XML sitemap for all public pages."""
    base_url = "https://happyheavens.in"
    today = timezone.now().date().isoformat()

    urls = []

    # Static pages
    static_pages = [
        ("", "1.0", "daily"),
        ("/customize/", "0.8", "monthly"),
    ]
    for path, priority, changefreq in static_pages:
        urls.append({
            "loc": f"{base_url}{path}",
            "lastmod": today,
            "changefreq": changefreq,
            "priority": priority,
        })

    # Category pages
    for cat in Category.objects.all():
        urls.append({
            "loc": f"{base_url}/category/{cat.slug}/",
            "lastmod": today,
            "changefreq": "weekly",
            "priority": "0.8",
        })

    # Product pages
    for product in Product.objects.filter(is_active=True).only("slug", "updated_at"):
        urls.append({
            "loc": f"{base_url}/product/{product.slug}/",
            "lastmod": product.updated_at.date().isoformat(),
            "changefreq": "weekly",
            "priority": "0.9",
        })

    # Build XML
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for url in urls:
        xml_parts.append("  <url>")
        xml_parts.append(f"    <loc>{url['loc']}</loc>")
        xml_parts.append(f"    <lastmod>{url['lastmod']}</lastmod>")
        xml_parts.append(f"    <changefreq>{url['changefreq']}</changefreq>")
        xml_parts.append(f"    <priority>{url['priority']}</priority>")
        xml_parts.append("  </url>")
    xml_parts.append("</urlset>")

    return HttpResponse("\n".join(xml_parts), content_type="application/xml")
