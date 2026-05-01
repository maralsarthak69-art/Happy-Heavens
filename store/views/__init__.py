# Re-export every view so existing imports (core/urls.py, error handlers) keep working.
from .products import product_list, product_detail, product_detail_by_pk, category_detail
from .cart import add_to_cart, remove_from_cart, cart_summary
from .checkout import checkout_view, order_success
from .orders import my_orders, order_detail
from .auth import signup_view, login_view, logout_view
from .customization import customize_idea, custom_request_success
from .search import search
from .errors import custom_404, custom_403, custom_500
from .newsletter import newsletter_subscribe
from .seo import robots_txt, sitemap_xml
from .dashboard import dashboard, dashboard_update_status, dashboard_stock, dashboard_update_stock

__all__ = [
    'product_list', 'product_detail', 'product_detail_by_pk', 'category_detail',
    'add_to_cart', 'remove_from_cart', 'cart_summary',
    'checkout_view', 'order_success',
    'my_orders', 'order_detail',
    'signup_view', 'login_view', 'logout_view',
    'customize_idea', 'custom_request_success',
    'search',
    'custom_404', 'custom_403', 'custom_500',
    'newsletter_subscribe',
    'robots_txt', 'sitemap_xml',
    'dashboard', 'dashboard_update_status',
    'dashboard_stock', 'dashboard_update_stock',
]
