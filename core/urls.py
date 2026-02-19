from django import views
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from store import views
from store.views import (
    product_list, product_detail, customize_idea, 
    add_to_cart, cart_summary, remove_from_cart, 
    search, category_detail,
    signup_view, login_view, logout_view, checkout_view, order_success
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', product_list, name='home'),
    path('product/<int:pk>/', product_detail, name='product_detail'),
    path('customize/', customize_idea, name='customize'),
    path('cart/', cart_summary, name='cart_summary'),
    path('add/<int:pk>/', add_to_cart, name='add_to_cart'),
    path('remove/<int:pk>/', remove_from_cart, name='remove_from_cart'),
    path('search/', search, name='search'),
    path('category/<slug:category_slug>/', views.category_detail, name='category_detail'),
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('my-orders/', views.my_orders, name='my_orders'),
]

# Serve Media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)