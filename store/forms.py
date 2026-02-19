from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import CustomRequest

# 1. YOUR EXISTING CUSTOM REQUEST FORM
class CustomRequestForm(forms.ModelForm):
    class Meta:
        model = CustomRequest
        fields = ['name', 'phone_number', 'idea_description', 'reference_image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-gray-50 border border-gray-200 p-4 text-xs tracking-widest uppercase focus:outline-none focus:border-black transition-colors', 'placeholder': 'YOUR NAME'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full bg-gray-50 border border-gray-200 p-4 text-xs tracking-widest uppercase focus:outline-none focus:border-black transition-colors', 'placeholder': 'PHONE / WHATSAPP'}),
            'idea_description': forms.Textarea(attrs={'class': 'w-full bg-gray-50 border border-gray-200 p-4 text-xs tracking-widest focus:outline-none focus:border-black transition-colors h-32', 'placeholder': 'DESCRIBE YOUR VISION...'}),
            'reference_image': forms.FileInput(attrs={'class': 'w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-[10px] file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200'}),
        }

# 2. UPDATED SIGNUP FORM (Now with Placeholders!)
class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Loop through every field and add the styling AND the placeholder
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full bg-gray-50 border border-gray-200 p-4 text-xs tracking-widest focus:outline-none focus:border-black transition-colors mb-4',
                'placeholder': field.label.upper() # <--- THIS PUTS THE TEXT INSIDE THE BOX
            })

# 3. UPDATED LOGIN FORM (Now with Placeholders!)
class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Loop through every field and add the styling AND the placeholder
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full bg-gray-50 border border-gray-200 p-4 text-xs tracking-widest focus:outline-none focus:border-black transition-colors mb-4',
                'placeholder': field.label.upper() # <--- THIS PUTS THE TEXT INSIDE THE BOX
            })