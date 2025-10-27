from django.db import models


class University(models.Model):
    """
    Model representing a university/college institution.
    Stores data from world_universities_and_domains.json (filtered to US only).
    """

    name = models.CharField(max_length=300, help_text="Official university name")
    country = models.CharField(max_length=100, default="United States")
    state_province = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="State or province (if available)",
    )
    alpha_two_code = models.CharField(
        max_length=2, default="US", help_text="ISO 3166-1 alpha-2 country code"
    )
    web_pages = models.TextField(
        blank=True, help_text="Comma-separated list of official web pages"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "University"
        verbose_name_plural = "Universities"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        return self.name

    def get_primary_domain(self):
        """Get the primary domain for this university."""
        primary = self.domains.filter(is_primary=True).first()
        return primary.domain if primary else None


class UniversityDomain(models.Model):
    """
    Model representing email domains associated with a university.
    Universities can have multiple domains (e.g., nyu.edu, students.nyu.edu).
    """

    university = models.ForeignKey(
        University, on_delete=models.CASCADE, related_name="domains"
    )
    domain = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Email domain (e.g., 'nyu.edu')",
    )
    is_primary = models.BooleanField(
        default=False, help_text="Is this the primary domain for the university?"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "University Domain"
        verbose_name_plural = "University Domains"
        ordering = ["-is_primary", "domain"]
        indexes = [
            models.Index(fields=["domain"]),
            models.Index(fields=["university", "is_primary"]),
        ]

    def __str__(self):
        primary_indicator = " (Primary)" if self.is_primary else ""
        return f"{self.domain}{primary_indicator} → {self.university.name}"

    def save(self, *args, **kwargs):
        """Normalize domain to lowercase before saving."""
        self.domain = self.domain.lower().strip()
        super().save(*args, **kwargs)
