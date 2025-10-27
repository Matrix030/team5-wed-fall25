from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
import re


def validation_edu_email(value):
    """
    Validates .edu email addresses, including subdomains (e.g., baruch.cuny.edu)
    """
    # Updated pattern to allow subdomains like baruch.cuny.edu
    edu_pattern = r"^[\w\.\+-]+@[\w\.-]+\.edu$"

    if not re.match(edu_pattern, value):
        raise ValidationError(
            "Please enter a valid .edu email address from your university"
        )


class User(AbstractUser):
    email = models.EmailField(unique=True, validators=[validation_edu_email])

    is_verified = models.BooleanField(default=False)

    # University domain validation fields
    validated_university = models.ForeignKey(
        "universities.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="University auto-detected from email domain",
    )
    domain_verified = models.BooleanField(
        default=False,
        help_text="Email domain was found in university database",
    )
    requires_admin_verification = models.BooleanField(
        default=False,
        help_text="Email domain not recognized, requires admin approval",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
