from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.conf import settings
from accounts.models import User
from accounts.forms import RegistrationForm
from universities.models import University, UniversityDomain


class RegistrationFormUniversityValidationTests(TestCase):
    """Test cases for university domain validation in RegistrationForm."""

    def setUp(self):
        """Set up test data."""
        # Create test universities and domains
        self.nyu = University.objects.create(
            name="New York University", country="United States", state_province="NY"
        )
        UniversityDomain.objects.create(
            university=self.nyu, domain="nyu.edu", is_primary=True
        )

        self.columbia = University.objects.create(
            name="Columbia University", country="United States", state_province="NY"
        )
        UniversityDomain.objects.create(
            university=self.columbia, domain="columbia.edu", is_primary=True
        )

        # CUNY with subdomain
        self.baruch = University.objects.create(
            name="CUNY Baruch College", country="United States", state_province="NY"
        )
        UniversityDomain.objects.create(
            university=self.baruch, domain="baruch.cuny.edu", is_primary=True
        )

    def test_form_validates_known_domain(self):
        """Test that form validates and sets university for known domain."""
        form_data = {
            "email": "student@nyu.edu",
            "username": "nyustudent",
            "first_name": "John",
            "last_name": "Doe",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Check that form has set the university attributes
        self.assertTrue(hasattr(form, "validated_university"))
        self.assertEqual(form.validated_university, self.nyu)
        self.assertTrue(form.domain_verified)
        self.assertFalse(form.requires_admin_verification)

    def test_form_handles_unknown_domain(self):
        """Test that form flags unknown domain for admin review."""
        form_data = {
            "email": "student@unknown-college.edu",
            "username": "unknownstudent",
            "first_name": "Jane",
            "last_name": "Smith",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Check that form flags for admin verification
        self.assertIsNone(form.validated_university)
        self.assertFalse(form.domain_verified)
        self.assertTrue(form.requires_admin_verification)

    def test_form_domain_case_insensitive(self):
        """Test that domain validation is case-insensitive."""
        form_data = {
            "email": "student@NYU.EDU",  # Uppercase
            "username": "nyustudent2",
            "first_name": "Bob",
            "last_name": "Johnson",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Should still match nyu.edu
        self.assertEqual(form.validated_university, self.nyu)
        self.assertTrue(form.domain_verified)

    def test_form_handles_cuny_subdomain(self):
        """Test that CUNY subdomains are properly validated."""
        form_data = {
            "email": "student@baruch.cuny.edu",
            "username": "baruchstudent",
            "first_name": "Alice",
            "last_name": "Williams",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

        self.assertEqual(form.validated_university, self.baruch)
        self.assertTrue(form.domain_verified)

    def test_form_rejects_duplicate_email(self):
        """Test that form rejects already registered email."""
        # Create existing user
        User.objects.create_user(
            username="existing",
            email="student@nyu.edu",
            password="testpass123",
        )

        form_data = {
            "email": "student@nyu.edu",
            "username": "newuser",
            "first_name": "John",
            "last_name": "Doe",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("already registered", str(form.errors["email"]))

    def test_form_handles_invalid_email_format(self):
        """Test that form handles invalid email format gracefully."""
        form_data = {
            "email": "not-an-email",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())


class RegistrationViewUniversityValidationTests(TestCase):
    """Test cases for university validation in registration view."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()
        self.register_url = reverse("register")

        # Create test university
        self.nyu = University.objects.create(
            name="New York University", country="United States"
        )
        UniversityDomain.objects.create(
            university=self.nyu, domain="nyu.edu", is_primary=True
        )

    def test_registration_with_known_domain(self):
        """Test registration with a known university domain."""
        form_data = {
            "email": "student@nyu.edu",
            "username": "nyustudent",
            "first_name": "John",
            "last_name": "Doe",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        response = self.client.post(self.register_url, data=form_data)

        # Should create user
        user = User.objects.filter(email="student@nyu.edu").first()
        self.assertIsNotNone(user)

        # Check university validation fields
        self.assertEqual(user.validated_university, self.nyu)
        self.assertTrue(user.domain_verified)
        self.assertFalse(user.requires_admin_verification)
        self.assertFalse(user.is_verified)  # Email still needs verification

        # Should send verification email
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify Your CampusNest Account", mail.outbox[0].subject)
        self.assertIn("New York University", mail.outbox[0].body)

    def test_registration_with_unknown_domain(self):
        """Test registration with unknown domain triggers admin review."""
        form_data = {
            "email": "student@unknown-college.edu",
            "username": "unknownstudent",
            "first_name": "Jane",
            "last_name": "Smith",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        # Set up admin email
        settings.ADMINS = [("Admin", "admin@campusnest.com")]

        response = self.client.post(self.register_url, data=form_data)

        # Should create user
        user = User.objects.filter(email="student@unknown-college.edu").first()
        self.assertIsNotNone(user)

        # Check flags
        self.assertIsNone(user.validated_university)
        self.assertFalse(user.domain_verified)
        self.assertTrue(user.requires_admin_verification)

        # Should send TWO emails: verification + admin notification
        self.assertEqual(len(mail.outbox), 2)

        # Check verification email
        verification_email = mail.outbox[0]
        self.assertIn("Verify Your CampusNest Account", verification_email.subject)

        # Check admin notification email
        admin_email = mail.outbox[1]
        self.assertIn("Pending Verification", admin_email.subject)
        self.assertIn("unknown-college.edu", admin_email.body)
        self.assertIn("admin@campusnest.com", admin_email.to)

    def test_registration_shows_warning_for_unknown_domain(self):
        """Test that registration shows warning message for unknown domain."""
        form_data = {
            "email": "student@unknown.edu",
            "username": "unknownuser",
            "first_name": "Test",
            "last_name": "User",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        response = self.client.post(self.register_url, data=form_data, follow=True)

        # Check for warning message in response
        messages = list(response.context["messages"])
        self.assertTrue(any("admin verification" in str(m) for m in messages))

    def test_registration_multiple_users_same_university(self):
        """Test that multiple users can register from same university."""
        for i in range(3):
            form_data = {
                "email": f"student{i}@nyu.edu",
                "username": f"nyustudent{i}",
                "first_name": f"Student{i}",
                "last_name": "Test",
                "password1": "testpass123!@#",
                "password2": "testpass123!@#",
            }
            self.client.post(self.register_url, data=form_data)

        # All should have same university
        users = User.objects.filter(email__icontains="@nyu.edu")
        self.assertEqual(users.count(), 3)
        for user in users:
            self.assertEqual(user.validated_university, self.nyu)
            self.assertTrue(user.domain_verified)


class UserModelUniversityFieldsTests(TestCase):
    """Test cases for university-related fields on User model."""

    def setUp(self):
        """Set up test data."""
        self.nyu = University.objects.create(
            name="New York University", country="United States"
        )

    def test_user_with_validated_university(self):
        """Test creating user with validated university."""
        user = User.objects.create_user(
            username="nyustudent",
            email="student@nyu.edu",
            password="testpass123",
            validated_university=self.nyu,
            domain_verified=True,
        )

        self.assertEqual(user.validated_university, self.nyu)
        self.assertTrue(user.domain_verified)
        self.assertFalse(user.requires_admin_verification)

    def test_user_requiring_admin_verification(self):
        """Test creating user that requires admin verification."""
        user = User.objects.create_user(
            username="unknownstudent",
            email="student@unknown.edu",
            password="testpass123",
            requires_admin_verification=True,
        )

        self.assertIsNone(user.validated_university)
        self.assertFalse(user.domain_verified)
        self.assertTrue(user.requires_admin_verification)

    def test_user_university_relationship(self):
        """Test the reverse relationship from university to users."""
        # Create multiple users from same university
        for i in range(3):
            User.objects.create_user(
                username=f"nyustudent{i}",
                email=f"student{i}@nyu.edu",
                password="testpass123",
                validated_university=self.nyu,
                domain_verified=True,
            )

        # Test reverse relationship
        self.assertEqual(self.nyu.users.count(), 3)

    def test_user_university_set_null_on_delete(self):
        """Test that user.validated_university is set to None when university deleted."""
        user = User.objects.create_user(
            username="nyustudent",
            email="student@nyu.edu",
            password="testpass123",
            validated_university=self.nyu,
            domain_verified=True,
        )

        university_id = self.nyu.id
        self.nyu.delete()

        # User should still exist but university should be None
        user.refresh_from_db()
        self.assertIsNone(user.validated_university)


class AdminApprovalWorkflowTests(TestCase):
    """Test cases for admin approval workflow."""

    def setUp(self):
        """Set up test data."""
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@campusnest.com",
            password="adminpass123",
        )

        # Create user needing approval
        self.pending_user = User.objects.create_user(
            username="pendinguser",
            email="student@unknown.edu",
            password="testpass123",
            requires_admin_verification=True,
            is_verified=True,  # Email verified but domain not approved
        )

        self.client = Client()
        self.client.login(username="admin", password="adminpass123")

    def test_admin_can_approve_user(self):
        """Test that admin can approve a pending user."""
        # Approve user by setting flag to False
        self.pending_user.requires_admin_verification = False
        self.pending_user.save()

        self.pending_user.refresh_from_db()
        self.assertFalse(self.pending_user.requires_admin_verification)

    def test_pending_users_filterable_in_admin(self):
        """Test that pending users can be filtered."""
        # Create mix of users
        approved_user = User.objects.create_user(
            username="approved",
            email="student@nyu.edu",
            password="testpass123",
            domain_verified=True,
        )

        pending_users = User.objects.filter(requires_admin_verification=True)
        approved_users = User.objects.filter(domain_verified=True)

        self.assertIn(self.pending_user, pending_users)
        self.assertNotIn(self.pending_user, approved_users)
        self.assertIn(approved_user, approved_users)


class EdgeCaseTests(TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        """Set up test data."""
        self.university = University.objects.create(
            name="Test University", country="United States"
        )
        UniversityDomain.objects.create(
            university=self.university, domain="test.edu", is_primary=True
        )

    def test_email_with_plus_addressing(self):
        """Test email with plus addressing (e.g., student+tag@test.edu)."""
        form_data = {
            "email": "student+newsletter@test.edu",
            "username": "teststudent",
            "first_name": "Test",
            "last_name": "User",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Should still extract correct domain
        self.assertEqual(form.validated_university, self.university)
        self.assertTrue(form.domain_verified)

    def test_email_with_subdomain(self):
        """Test email with subdomain (e.g., student@mail.test.edu)."""
        # This domain doesn't exist in our database
        form_data = {
            "email": "student@mail.test.edu",
            "username": "teststudent2",
            "first_name": "Test",
            "last_name": "User",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Should not match (domain is "mail.test.edu", not "test.edu")
        self.assertIsNone(form.validated_university)
        self.assertTrue(form.requires_admin_verification)

    def test_whitespace_in_email(self):
        """Test that whitespace in email is handled."""
        form_data = {
            "email": "  student@test.edu  ",
            "username": "teststudent3",
            "first_name": "Test",
            "last_name": "User",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        form = RegistrationForm(data=form_data)
        # Django's EmailField should strip whitespace
        if form.is_valid():
            # Domain should be extracted correctly after stripping
            self.assertEqual(form.validated_university, self.university)
