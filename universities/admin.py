from django.contrib import admin
from .models import University, UniversityDomain


class UniversityDomainInline(admin.TabularInline):
    """Inline display of domains for a university."""

    model = UniversityDomain
    extra = 0  # Don't show empty rows
    fields = ["domain", "is_primary", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    """Admin interface for University model."""

    list_display = [
        "name",
        "state_province",
        "country",
        "domain_count",
        "user_count",
        "created_at",
    ]
    list_filter = ["country", "state_province"]
    search_fields = ["name", "domains__domain"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [UniversityDomainInline]

    fieldsets = (
        (
            "University Information",
            {
                "fields": (
                    "name",
                    "country",
                    "state_province",
                    "alpha_two_code",
                    "web_pages",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def domain_count(self, obj):
        """Display number of domains for this university."""
        return obj.domains.count()

    domain_count.short_description = "Domains"

    def user_count(self, obj):
        """Display number of users from this university."""
        return obj.users.count()

    user_count.short_description = "Users"


@admin.register(UniversityDomain)
class UniversityDomainAdmin(admin.ModelAdmin):
    """Admin interface for UniversityDomain model."""

    list_display = ["domain", "university", "is_primary", "user_count", "created_at"]
    list_filter = ["is_primary", "university__country"]
    search_fields = ["domain", "university__name"]
    readonly_fields = ["created_at"]
    autocomplete_fields = ["university"]

    fieldsets = (
        (
            "Domain Information",
            {
                "fields": ("domain", "university", "is_primary")
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    def user_count(self, obj):
        """Display number of users registered with this domain."""
        # Count users where email domain matches this domain
        from accounts.models import User

        return User.objects.filter(
            email__icontains=f"@{obj.domain}"
        ).count()

    user_count.short_description = "Users"
