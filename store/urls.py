"""
Store app URL patterns.
Grouped by domain so adding a new feature means adding a block here,
not hunting through a monolithic core/urls.py.
"""
from django.urls import path
from store.views import (
    # Products
    product_list, product_detail, product_detail_by_pk, category_detail,
    # Cart
    add_to_cart, remove_from_cart, cart_summary,
    # Checkout & orders
    checkout_view, order_success, my_orders, order_detail,
    # Auth
    signup_view, login_view, logout_view,
    # Customization
    customize_idea, custom_request_success,
    # Search
    search,
    # Newsletter
    newsletter_subscribe,
    # SEO
    robots_txt, sitemap_xml,
)

urlpatterns = [
    # --- Products & Catalogue ---
    path('', product_list, name='home'),
    path('product/<slug:slug>/', product_detail, name='product_detail'),
    path('product/<int:pk>/redirect/', product_detail_by_pk, name='product_detail_by_pk'),
    path('category/<slug:category_slug>/', category_detail, name='category_detail'),
    path('search/', search, name='search'),

    # --- Cart ---
    path('cart/', cart_summary, name='cart_summary'),
    path('cart/add/<int:pk>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:pk>/', remove_from_cart, name='remove_from_cart'),

    # --- Checkout & Orders ---
    path('checkout/', checkout_view, name='checkout'),
    path('checkout/success/<int:order_id>/', order_success, name='order_success'),
    path('orders/', my_orders, name='my_orders'),
    path('orders/<int:pk>/', order_detail, name='order_detail'),

    # --- Customization ---
    path('customize/', customize_idea, name='customize'),
    path('customize/success/', custom_request_success, name='custom_request_success'),

    # --- Auth ---
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # --- Newsletter ---
    path('newsletter/subscribe/', newsletter_subscribe, name='newsletter_subscribe'),

    # --- SEO ---
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
]
