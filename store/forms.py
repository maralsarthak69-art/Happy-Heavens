from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import MinimumLengthValidator, NumericPasswordValidator
from django.core.exceptions import ValidationError
from .models import CustomRequest
from .utils import clean_required_text

INPUT_CLASS = (
    'w-full bg-gray-50 border border-gray-200 p-4 text-xs tracking-widest '
    'focus:outline-none focus:border-black transition-colors'
)


class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = (
        ('QR', 'Scan QR & Upload'),
        ('COD', 'Cash on Delivery'),
    )

    full_name     = forms.CharField(max_length=255)
    phone_number  = forms.CharField(max_length=15)
    address       = forms.CharField(widget=forms.Textarea)
    city          = forms.CharField(max_length=100)
    pincode       = forms.CharField(max_length=10)
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES)

    def clean_full_name(self):
        return clean_required_text(self.cleaned_data.get('full_name', ''), 'Full name')

    def clean_phone_number(self):
        return clean_required_text(self.cleaned_data.get('phone_number', ''), 'Phone number')

    def clean_address(self):
        return clean_required_text(self.cleaned_data.get('address', ''), 'Address')

    def clean_city(self):
        return clean_required_text(self.cleaned_data.get('city', ''), 'City')

    def clean_pincode(self):
        return clean_required_text(self.cleaned_data.get('pincode', ''), 'Pincode')


class CustomRequestForm(forms.ModelForm):
    class Meta:
        model = CustomRequest
        fields = ['name', 'phone_number', 'idea_description', 'reference_image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASS, 'placeholder': 'YOUR NAME',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': INPUT_CLASS, 'placeholder': 'PHONE / WHATSAPP',
            }),
            'idea_description': forms.Textarea(attrs={
                'class': INPUT_CLASS + ' h-32', 'placeholder': 'DESCRIBE YOUR VISION...',
            }),
            'reference_image': forms.FileInput(attrs={
                'class': (
                    'w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 '
                    'file:rounded-full file:border-0 file:text-[10px] file:font-semibold '
                    'file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200'
                ),
            }),
        }

    def clean_name(self):
        return clean_required_text(self.cleaned_data.get('name', ''), 'Name')

    def clean_phone_number(self):
        return clean_required_text(self.cleaned_data.get('phone_number', ''), 'Phone number')

    def clean_idea_description(self):
        return clean_required_text(self.cleaned_data.get('idea_description', ''), 'Idea description')


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': INPUT_CLASS + ' mb-4',
                'placeholder': field.label.upper(),
            })

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validators = [MinimumLengthValidator(min_length=8), NumericPasswordValidator()]
            errors = []
            for validator in validators:
                try:
                    validator.validate(password)
                except ValidationError as e:
                    errors.extend(e.messages)
            if errors:
                raise forms.ValidationError(errors)
        return password


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': INPUT_CLASS + ' mb-4',
                'placeholder': field.label.upper(),
            })
