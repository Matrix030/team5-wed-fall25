from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.mail import send_mail
from django.conf import settings
from .models import User


class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model with university verification
    """

    # Fields to display in the user list
    list_display = [
        "email",
        "username",
        "first_name",
        "last_name",
        "validated_university",
        "domain_verified_icon",
        "requires_verification_icon",
        "is_verified",
        "is_staff",
        "date_joined",
    ]

    # Fields you can click to open user detail
    list_display_links = ["email", "username"]

    # Add filters in the sidebar
    list_filter = [
        "requires_admin_verification",
        "domain_verified",
        "is_verified",
        "is_staff",
        "is_superuser",
        "is_active",
        "date_joined",
    ]

    # Add search functionality
    search_fields = [
        "email",
        "username",
        "first_name",
        "last_name",
        "validated_university__name",
    ]

    # Fields to show when editing a user
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        (
            "University Verification",
            {
                "fields": (
                    "validated_university",
                    "domain_verified",
                    "requires_admin_verification",
                ),
                "description": "University domain validation status",
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )

    # Fields to show when adding a new user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "is_verified",
                ),
            },
        ),
    )

    # Default ordering - show pending verification users first
    ordering = ["-requires_admin_verification", "-date_joined"]

    # Custom display methods
    def domain_verified_icon(self, obj):
        """Display checkmark/cross for domain verification status."""
        if obj.domain_verified:
            return "✅"
        return "❌"

    domain_verified_icon.short_description = "Domain Verified"

    def requires_verification_icon(self, obj):
        """Display warning icon if requires admin verification."""
        if obj.requires_admin_verification:
            return "⚠️ PENDING"
        return "✓"

    requires_verification_icon.short_description = "Admin Review"

    # Admin actions
    actions = ["approve_pending_users"]

    def approve_pending_users(self, request, queryset):
        """
        Admin action to approve users pending verification.
        Clears requires_admin_verification flag and sends approval email.
        """
        approved_count = 0

        for user in queryset.filter(requires_admin_verification=True):
            user.requires_admin_verification = False
            user.save()

            # Send approval email
            subject = "Your CampusNest Account Has Been Approved"
            message = f"""
            Hi {user.first_name},

            Great news! Your CampusNest account has been approved by our admin team.

            Email: {user.email}

            You can now log in and access all features of CampusNest:
            http://{request.get_host()}/accounts/login/

            Welcome to the CampusNest community!

            Best regards,
            The CampusNest Team
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )

            approved_count += 1

        self.message_user(
            request, f"Successfully approved {approved_count} user(s) and sent notification emails."
        )

    approve_pending_users.short_description = "Approve selected users pending verification"


# Register the custom User model with custom admin
admin.site.register(User, UserAdmin)
