from django.shortcuts import render, redirect

from store.forms import CustomRequestForm


def customize_idea(request):
    """Handles the 'Customize Your Ideas' form submission."""
    if request.method == 'POST':
        form = CustomRequestForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('custom_request_success')
    else:
        form = CustomRequestForm()
    return render(request, 'customize.html', {'form': form})


def custom_request_success(request):
    """Confirmation page after a successful custom request."""
    return render(request, 'customize_success.html')
