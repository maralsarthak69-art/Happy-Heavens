from django import forms


def clean_required_text(value: str, field_name: str) -> str:
    """
    Strip whitespace and raise ValidationError if the result is empty.
    Reusable across all forms that need non-blank required text fields.
    """
    stripped = value.strip() if value else ''
    if not stripped:
        raise forms.ValidationError(f"{field_name} is required.")
    return stripped
