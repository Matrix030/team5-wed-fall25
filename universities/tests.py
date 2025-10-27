import json
import tempfile
import os
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django.db import IntegrityError
from universities.models import University, UniversityDomain


# ============================================================================
# MODEL TESTS
# ============================================================================


class UniversityModelTests(TestCase):
    """Test cases for the University model."""

    def setUp(self):
        """Set up test data."""
        self.university_data = {
            "name": "Test University",
            "country": "United States",
            "state_province": "New York",
            "alpha_two_code": "US",
            "web_pages": "https://test.edu, https://www.test.edu",
        }

    def test_create_university(self):
        """Test creating a university with valid data."""
        university = University.objects.create(**self.university_data)

        self.assertEqual(university.name, "Test University")
        self.assertEqual(university.country, "United States")
        self.assertEqual(university.state_province, "New York")
        self.assertEqual(university.alpha_two_code, "US")
        self.assertIsNotNone(university.created_at)
        self.assertIsNotNone(university.updated_at)

    def test_university_str_representation(self):
        """Test the string representation of University."""
        university = University.objects.create(**self.university_data)
        self.assertEqual(str(university), "Test University")

    def test_university_ordering(self):
        """Test that universities are ordered by name."""
        University.objects.create(name="Zebra University", country="United States")
        University.objects.create(name="Alpha University", country="United States")
        University.objects.create(name="Beta University", country="United States")

        universities = list(University.objects.all())
        self.assertEqual(universities[0].name, "Alpha University")
        self.assertEqual(universities[1].name, "Beta University")
        self.assertEqual(universities[2].name, "Zebra University")

    def test_get_primary_domain(self):
        """Test getting the primary domain for a university."""
        university = University.objects.create(**self.university_data)
        UniversityDomain.objects.create(
            university=university, domain="test.edu", is_primary=True
        )
        UniversityDomain.objects.create(
            university=university, domain="alumni.test.edu", is_primary=False
        )

        primary_domain = university.get_primary_domain()
        self.assertEqual(primary_domain, "test.edu")

    def test_get_primary_domain_none(self):
        """Test getting primary domain when none exists."""
        university = University.objects.create(**self.university_data)
        primary_domain = university.get_primary_domain()
        self.assertIsNone(primary_domain)

    def test_university_without_state(self):
        """Test creating university without state_province."""
        university = University.objects.create(
            name="Online University", country="United States", alpha_two_code="US"
        )
        self.assertIsNone(university.state_province)


class UniversityDomainModelTests(TestCase):
    """Test cases for the UniversityDomain model."""

    def setUp(self):
        """Set up test data."""
        self.university = University.objects.create(
            name="Test University", country="United States"
        )

    def test_create_domain(self):
        """Test creating a university domain."""
        domain = UniversityDomain.objects.create(
            university=self.university, domain="test.edu", is_primary=True
        )

        self.assertEqual(domain.university, self.university)
        self.assertEqual(domain.domain, "test.edu")
        self.assertTrue(domain.is_primary)
        self.assertIsNotNone(domain.created_at)

    def test_domain_lowercase_normalization(self):
        """Test that domains are normalized to lowercase."""
        domain = UniversityDomain.objects.create(
            university=self.university, domain="TEST.EDU", is_primary=True
        )

        self.assertEqual(domain.domain, "test.edu")

    def test_domain_strip_whitespace(self):
        """Test that domains have whitespace stripped."""
        domain = UniversityDomain.objects.create(
            university=self.university, domain="  test.edu  ", is_primary=True
        )

        self.assertEqual(domain.domain, "test.edu")

    def test_domain_uniqueness(self):
        """Test that domains must be unique across all universities."""
        UniversityDomain.objects.create(
            university=self.university, domain="test.edu", is_primary=True
        )

        # Try to create another domain with same value
        university2 = University.objects.create(
            name="Another University", country="United States"
        )

        with self.assertRaises(IntegrityError):
            UniversityDomain.objects.create(
                university=university2, domain="test.edu", is_primary=True
            )

    def test_domain_str_representation(self):
        """Test the string representation of UniversityDomain."""
        domain = UniversityDomain.objects.create(
            university=self.university, domain="test.edu", is_primary=True
        )

        expected = "test.edu (Primary) → Test University"
        self.assertEqual(str(domain), expected)

    def test_domain_str_non_primary(self):
        """Test string representation for non-primary domain."""
        domain = UniversityDomain.objects.create(
            university=self.university, domain="alumni.test.edu", is_primary=False
        )

        expected = "alumni.test.edu → Test University"
        self.assertEqual(str(domain), expected)

    def test_multiple_domains_per_university(self):
        """Test that a university can have multiple domains."""
        UniversityDomain.objects.create(
            university=self.university, domain="test.edu", is_primary=True
        )
        UniversityDomain.objects.create(
            university=self.university, domain="alumni.test.edu", is_primary=False
        )
        UniversityDomain.objects.create(
            university=self.university, domain="students.test.edu", is_primary=False
        )

        self.assertEqual(self.university.domains.count(), 3)

    def test_domain_ordering(self):
        """Test that domains are ordered with primary first."""
        UniversityDomain.objects.create(
            university=self.university, domain="alumni.test.edu", is_primary=False
        )
        UniversityDomain.objects.create(
            university=self.university, domain="test.edu", is_primary=True
        )
        UniversityDomain.objects.create(
            university=self.university, domain="students.test.edu", is_primary=False
        )

        domains = list(self.university.domains.all())
        self.assertTrue(domains[0].is_primary)
        self.assertEqual(domains[0].domain, "test.edu")

    def test_domain_cascade_delete(self):
        """Test that domains are deleted when university is deleted."""
        UniversityDomain.objects.create(
            university=self.university, domain="test.edu", is_primary=True
        )
        UniversityDomain.objects.create(
            university=self.university, domain="alumni.test.edu", is_primary=False
        )

        university_id = self.university.id
        self.university.delete()

        # Domains should be deleted
        self.assertEqual(
            UniversityDomain.objects.filter(university_id=university_id).count(), 0
        )

    def test_case_insensitive_domain_lookup(self):
        """Test that domain lookups are case-insensitive (due to normalization)."""
        UniversityDomain.objects.create(
            university=self.university, domain="TEST.EDU", is_primary=True
        )

        # Should find the domain regardless of case in query
        domain = UniversityDomain.objects.filter(domain="test.edu").first()
        self.assertIsNotNone(domain)
        self.assertEqual(domain.university, self.university)


class UniversityDomainIntegrationTests(TestCase):
    """Integration tests for University and UniversityDomain models."""

    def test_university_with_multiple_domains_query_efficiency(self):
        """Test that related domain queries are efficient."""
        university = University.objects.create(
            name="Large University", country="United States"
        )

        # Create multiple domains
        for i in range(10):
            UniversityDomain.objects.create(
                university=university,
                domain=f"domain{i}.edu",
                is_primary=(i == 0),
            )

        # Query with prefetch_related requires 2 queries (1 for university, 1 for domains)
        with self.assertNumQueries(2):
            uni = University.objects.prefetch_related("domains").get(
                id=university.id
            )
            list(uni.domains.all())  # Force evaluation

    def test_domain_lookup_by_email(self):
        """Test looking up university by email domain."""
        nyu = University.objects.create(
            name="New York University", country="United States", state_province="NY"
        )
        UniversityDomain.objects.create(
            university=nyu, domain="nyu.edu", is_primary=True
        )

        # Simulate email domain extraction
        email = "student@nyu.edu"
        domain = email.split("@")[1].lower()

        found_domain = UniversityDomain.objects.filter(domain=domain).first()
        self.assertIsNotNone(found_domain)
        self.assertEqual(found_domain.university.name, "New York University")

    def test_cuny_subdomain_handling(self):
        """Test handling of CUNY subdomains (e.g., baruch.cuny.edu)."""
        baruch = University.objects.create(
            name="CUNY Baruch College", country="United States", state_province="NY"
        )
        UniversityDomain.objects.create(
            university=baruch, domain="baruch.cuny.edu", is_primary=True
        )

        hunter = University.objects.create(
            name="Hunter College CUNY", country="United States", state_province="NY"
        )
        UniversityDomain.objects.create(
            university=hunter, domain="hunter.cuny.edu", is_primary=True
        )

        # Test that different CUNY subdomains are distinct
        email1 = "student@baruch.cuny.edu"
        domain1 = email1.split("@")[1].lower()
        found1 = UniversityDomain.objects.filter(domain=domain1).first()
        self.assertEqual(found1.university.name, "CUNY Baruch College")

        email2 = "student@hunter.cuny.edu"
        domain2 = email2.split("@")[1].lower()
        found2 = UniversityDomain.objects.filter(domain=domain2).first()
        self.assertEqual(found2.university.name, "Hunter College CUNY")

    def test_university_user_count(self):
        """Test counting users from a university."""
        from accounts.models import User

        nyu = University.objects.create(
            name="New York University", country="United States"
        )
        UniversityDomain.objects.create(
            university=nyu, domain="nyu.edu", is_primary=True
        )

        # Create users with validated university
        for i in range(3):
            User.objects.create_user(
                username=f"nyustudent{i}",
                email=f"student{i}@nyu.edu",
                password="testpass123",
                validated_university=nyu,
                domain_verified=True,
            )

        self.assertEqual(nyu.users.count(), 3)


# ============================================================================
# MANAGEMENT COMMAND TESTS
# ============================================================================


class ImportUniversitiesCommandTests(TestCase):
    """Test cases for import_universities management command."""

    def setUp(self):
        """Set up test data."""
        # Create sample JSON data for testing
        self.test_data = [
            {
                "name": "Test University 1",
                "domains": ["test1.edu"],
                "web_pages": ["https://test1.edu"],
                "country": "United States",
                "alpha_two_code": "US",
                "state-province": "New York",
            },
            {
                "name": "Test University 2",
                "domains": ["test2.edu", "alumni.test2.edu"],
                "web_pages": ["https://test2.edu"],
                "country": "United States",
                "alpha_two_code": "US",
                "state-province": None,
            },
            {
                "name": "Foreign University",
                "domains": ["foreign.ac.uk"],
                "web_pages": ["https://foreign.ac.uk"],
                "country": "United Kingdom",
                "alpha_two_code": "GB",
                "state-province": None,
            },
            {
                "name": "University Without Domain",
                "domains": [],
                "web_pages": ["https://nodomain.edu"],
                "country": "United States",
                "alpha_two_code": "US",
                "state-province": None,
            },
        ]

        # Create temporary JSON file
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(self.test_data, self.temp_file)
        self.temp_file.close()

    def tearDown(self):
        """Clean up temporary file."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_command_imports_us_universities_only(self):
        """Test that command only imports US universities."""
        out = StringIO()
        call_command("import_universities", file=self.temp_file.name, stdout=out)

        # Should import only US universities
        self.assertEqual(University.objects.count(), 2)

        # Check specific universities
        self.assertTrue(University.objects.filter(name="Test University 1").exists())
        self.assertTrue(University.objects.filter(name="Test University 2").exists())
        self.assertFalse(University.objects.filter(name="Foreign University").exists())

    def test_command_imports_multiple_domains(self):
        """Test that command imports all domains for a university."""
        out = StringIO()
        call_command("import_universities", file=self.temp_file.name, stdout=out)

        # Test University 2 should have 2 domains
        uni2 = University.objects.get(name="Test University 2")
        self.assertEqual(uni2.domains.count(), 2)

        # Check domain names
        domain_names = set(uni2.domains.values_list("domain", flat=True))
        self.assertIn("test2.edu", domain_names)
        self.assertIn("alumni.test2.edu", domain_names)

    def test_command_sets_primary_domain(self):
        """Test that first domain is marked as primary."""
        out = StringIO()
        call_command("import_universities", file=self.temp_file.name, stdout=out)

        uni2 = University.objects.get(name="Test University 2")
        primary_domain = uni2.domains.filter(is_primary=True).first()

        self.assertIsNotNone(primary_domain)
        self.assertEqual(primary_domain.domain, "test2.edu")

    def test_command_skips_universities_without_domains(self):
        """Test that universities without domains are skipped."""
        out = StringIO()
        call_command("import_universities", file=self.temp_file.name, stdout=out)

        # Should skip "University Without Domain"
        self.assertFalse(
            University.objects.filter(name="University Without Domain").exists()
        )

    def test_command_dry_run_mode(self):
        """Test that dry-run mode doesn't create any records."""
        out = StringIO()
        call_command(
            "import_universities", file=self.temp_file.name, dry_run=True, stdout=out
        )

        # Should not create any records
        self.assertEqual(University.objects.count(), 0)
        self.assertEqual(UniversityDomain.objects.count(), 0)

        # But should report what would be imported
        output = out.getvalue()
        self.assertIn("Found 3 US universities", output)
        self.assertIn("DRY RUN MODE", output)

    def test_command_clear_mode(self):
        """Test that clear mode removes existing data before importing."""
        # Create existing data
        existing_uni = University.objects.create(
            name="Existing University", country="United States"
        )
        UniversityDomain.objects.create(
            university=existing_uni, domain="existing.edu", is_primary=True
        )

        out = StringIO()
        call_command(
            "import_universities", file=self.temp_file.name, clear=True, stdout=out
        )

        # Old data should be gone
        self.assertFalse(
            University.objects.filter(name="Existing University").exists()
        )

        # New data should exist
        self.assertTrue(University.objects.filter(name="Test University 1").exists())

    def test_command_handles_duplicate_universities(self):
        """Test that command handles duplicate university names gracefully."""
        # Pre-create one of the universities
        University.objects.create(name="Test University 1", country="United States")

        out = StringIO()
        call_command("import_universities", file=self.temp_file.name, stdout=out)

        # Should only have one instance of Test University 1
        self.assertEqual(
            University.objects.filter(name="Test University 1").count(), 1
        )

    def test_command_output_format(self):
        """Test that command output includes summary information."""
        out = StringIO()
        call_command("import_universities", file=self.temp_file.name, stdout=out)

        output = out.getvalue()

        # Should include summary
        self.assertIn("Import completed", output)
        self.assertIn("Universities created:", output)
        self.assertIn("Domains created:", output)

        # Should include sample universities
        self.assertIn("Sample of imported universities:", output)

    def test_command_handles_missing_file(self):
        """Test that command handles missing file gracefully."""
        out = StringIO()
        err = StringIO()

        call_command(
            "import_universities",
            file="nonexistent_file.json",
            stdout=out,
            stderr=err,
        )

        output = out.getvalue() + err.getvalue()
        self.assertIn("File not found", output)

    def test_command_handles_invalid_json(self):
        """Test that command handles invalid JSON gracefully."""
        # Create file with invalid JSON
        invalid_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        invalid_file.write("{ invalid json }")
        invalid_file.close()

        try:
            out = StringIO()
            err = StringIO()

            call_command(
                "import_universities",
                file=invalid_file.name,
                stdout=out,
                stderr=err,
            )

            output = out.getvalue() + err.getvalue()
            self.assertIn("Invalid JSON", output)
        finally:
            os.unlink(invalid_file.name)

    def test_command_batch_processing(self):
        """Test that command processes universities in batches."""
        # Create larger dataset
        large_data = []
        for i in range(150):  # More than one batch (batch_size=100)
            large_data.append(
                {
                    "name": f"University {i}",
                    "domains": [f"uni{i}.edu"],
                    "web_pages": [f"https://uni{i}.edu"],
                    "country": "United States",
                    "alpha_two_code": "US",
                    "state-province": None,
                }
            )

        temp_large = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(large_data, temp_large)
        temp_large.close()

        try:
            out = StringIO()
            call_command("import_universities", file=temp_large.name, stdout=out)

            output = out.getvalue()

            # Should show batch processing
            self.assertIn("Processing batch 1", output)
            self.assertIn("Processing batch 2", output)

            # Should import all universities
            self.assertEqual(University.objects.count(), 150)
        finally:
            os.unlink(temp_large.name)

    def test_command_preserves_web_pages(self):
        """Test that command preserves web_pages field."""
        out = StringIO()
        call_command("import_universities", file=self.temp_file.name, stdout=out)

        uni1 = University.objects.get(name="Test University 1")
        self.assertEqual(uni1.web_pages, "https://test1.edu")

    def test_command_preserves_state_province(self):
        """Test that command preserves state_province field."""
        out = StringIO()
        call_command("import_universities", file=self.temp_file.name, stdout=out)

        uni1 = University.objects.get(name="Test University 1")
        self.assertEqual(uni1.state_province, "New York")

        uni2 = University.objects.get(name="Test University 2")
        self.assertIsNone(uni2.state_province)
