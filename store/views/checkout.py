from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from store.cart import Cart
from store.forms import CheckoutForm
from store.models import Order
from store.exceptions import InsufficientStockError
from store.services.order_service import create_order


@login_required(login_url='/login/?next=/checkout/')
def checkout_view(request):
    """
    Handles the QR / COD payment workflow.
    Business logic (stock validation, order creation) is delegated to
    OrderService so this view stays thin and easy to extend.
    """
    cart = Cart(request)

    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('home')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)

        # QR requires a screenshot — check before any DB work
        if request.POST.get('payment_method') == 'QR' and not request.FILES.get('payment_screenshot'):
            form.add_error(None, "A payment screenshot is required for QR Code Transfer.")
            return render(request, 'checkout.html', {'cart': cart, 'form': form})

        if form.is_valid():
            # Snapshot cart once — avoids double DB iteration inside the service
            cart_items = list(cart)
            total = cart.get_total_price()

            try:
                order = create_order(
                    user=request.user,
                    form_data=form.cleaned_data,
                    cart_items=cart_items,
                    total=total,
                    payment_screenshot=request.FILES.get('payment_screenshot'),
                )
            except InsufficientStockError as e:
                return render(request, 'checkout.html', {
                    'cart': cart,
                    'form': form,
                    'stock_error': str(e),
                })

            cart.clear()
            return redirect('order_success', order_id=order.id)

        return render(request, 'checkout.html', {'cart': cart, 'form': form})

    return render(request, 'checkout.html', {'cart': cart, 'form': CheckoutForm()})


@login_required
def order_success(request, order_id):
    """Confirmation page shown after a successful order."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = order.items.select_related('product')
    return render(request, 'order_success.html', {'order': order, 'items': items})
