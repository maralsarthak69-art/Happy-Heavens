from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from store.models import Product
from store.cart import Cart


@require_POST
def add_to_cart(request, pk):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=pk)
    if product.stock == 0:
        messages.error(request, f'"{product.name}" is out of stock and cannot be added to your cart.')
        return redirect('product_detail', slug=product.slug)
    product_id = str(product.id)
    current_quantity = cart.cart.get(product_id, {}).get('quantity', 0)
    if current_quantity + 1 > product.stock:
        messages.error(request, f'Cannot add more "{product.name}" to your cart. Maximum available quantity is {product.stock}.')
        return redirect('product_detail', slug=product.slug)
    cart.add(product=product)
    return redirect('product_detail', slug=product.slug)


@require_POST
def remove_from_cart(request, pk):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=pk)
    cart.remove(product)
    return redirect('cart_summary')


def cart_summary(request):
    cart = Cart(request)
    return render(request, 'cart_summary.html', {'cart': cart})
