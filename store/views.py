from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .models import Product, Category, order, OrderItem #
from .forms import CustomRequestForm, SignUpForm, LoginForm
from .cart import Cart
from django.contrib.auth.decorators import login_required

# --- PRODUCT & HOME VIEWS ---

def product_list(request):
    """Powers the home page with the Split-Hero Slider and main grid."""
    products = Product.objects.all()
    # Fetch the 5 latest active products for the hero section
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    return render(request, 'index.html', {
        'products': products, 
        'new_arrivals': new_arrivals
    })

def product_detail(request, pk):
    """Displays the detail page for a specific handcrafted item."""
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})

def category_detail(request, category_slug):
    """Filters products by their specific category."""
    products = Product.objects.filter(category__slug=category_slug)
    category = get_object_or_404(Category, slug=category_slug)

    return render(request, 'category_detail.html', {
        'products': products, 
        'category': category
    })

# --- CART & CHECKOUT LOGIC ---
@login_required
def checkout_view(request):
    """Handles the manual QR/COD payment workflow."""
    cart = Cart(request)
    
    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('home')

    if request.method == 'POST':
        # FIX: Changed 'order' to 'new_order' to avoid shadowing the Model name
        new_order = order.objects.create(
            user=request.user,
            full_name=request.POST.get('full_name'),
            phone_number=request.POST.get('phone_number'),
            address=request.POST.get('address'),
            payment_method=request.POST.get('payment_method'),
            # .get() handles COD safely even if no file is uploaded
            payment_screenshot=request.FILES.get('payment_screenshot'),
            total_amount=cart.get_total_price()
        )

        # Move items from session cart to database OrderItems
        for item in cart:
            OrderItem.objects.create(
                order=new_order, # Use the new instance variable
                product=item['product'],
                quantity=item['quantity'],
                price=item['price']
            )
            
        # Clear the cart session entirely
        cart.clear()
        
        messages.success(request, "Order placed! Waiting for admin approval.")
        return render(request, 'order_success.html', {'order': new_order})
    
    return render(request, 'checkout.html', {'cart': cart})

def add_to_cart(request, pk):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=pk)
    cart.add(product=product)
    return redirect('product_detail', pk=pk)

def cart_summary(request):
    cart = Cart(request)
    return render(request, 'cart_summary.html', {'cart': cart})

def remove_from_cart(request, pk):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=pk)
    cart.remove(product)
    return redirect('cart_summary')

# --- CUSTOMIZATION & SEARCH ---

def customize_idea(request):
    """Handles the 'Customize Your Ideas' image and text submission."""
    if request.method == 'POST':
        form = CustomRequestForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return render(request, 'customize_success.html')
    else:
        form = CustomRequestForm()
    
    return render(request, 'customize.html', {'form': form})

def search(request):
    query = request.GET.get('q')
    results = []
    if query:
        results = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    return render(request, 'search_results.html', {'query': query, 'results': results})

# --- AUTHENTICATION VIEWS ---

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

def order_success(request):
    """
    Simple view to render the success page after a user 
    uploads their payment screenshot.
    """
    return render(request, 'order_success.html')

@login_required
def my_orders(request):
    """Displays a personalized order history for the logged-in user."""
    # Filter by user and order by newest first
    orders = order.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'my_orders.html', {'orders': orders})