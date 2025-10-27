from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from universities.models import UniversityDomain


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TelInput(attrs={"placeholder": "First Name"}),
    )

    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Last Name"}),
    )

    email = forms.EmailField(
        required=True, widget=forms.EmailInput(attrs={"placeholder": "Your .edu Email"})
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]

    def clean_email(self):
        email = self.cleaned_data.get("email")

        # Check if email already registered
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered")

        # Extract domain from email (part after @)
        try:
            domain = email.split("@")[1].lower().strip()
        except IndexError:
            raise forms.ValidationError("Invalid email format")

        # Check if domain exists in university database
        university_domain = (
            UniversityDomain.objects.filter(domain=domain)
            .select_related("university")
            .first()
        )

        if university_domain:
            # Domain found - store for later use in view
            self.validated_university = university_domain.university
            self.domain_verified = True
            self.requires_admin_verification = False
        else:
            # Domain not found - flag for admin review
            self.validated_university = None
            self.domain_verified = False
            self.requires_admin_verification = True

        return email
