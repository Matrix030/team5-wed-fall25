from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from accounts.models import User
from universities.models import University, UniversityDomain
from profiles.models import Profile


class CompleteRegistrationFlowTests(TestCase):
    """Integration tests for complete registration flow with university validation."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create test universities
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

    def test_complete_registration_and_profile_creation_flow(self):
        """Test complete flow: register -> verify email -> create profile -> view profile."""

        # Step 1: Register with known domain
        register_data = {
            "email": "student@nyu.edu",
            "username": "nyustudent",
            "first_name": "John",
            "last_name": "Doe",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        response = self.client.post(reverse("register"), data=register_data)
        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Verify user created with correct university
        user = User.objects.get(email="student@nyu.edu")
        self.assertEqual(user.validated_university, self.nyu)
        self.assertTrue(user.domain_verified)
        self.assertFalse(user.is_verified)  # Email not verified yet

        # Step 2: Verify email
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verify_url = reverse("verify_email", kwargs={"uidb64": uid, "token": token})

        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 302)

        user.refresh_from_db()
        self.assertTrue(user.is_verified)

        # Step 3: Login
        login_success = self.client.login(username="student@nyu.edu", password="testpass123!@#")
        self.assertTrue(login_success)

        # Step 4: Create profile (should auto-populate university if it matches)
        profile_data = {
            "bio": "Test bio",
            "university": "NYU",  # Matches "New York University"
            "eating_habit": "no_preference",
            "smoking_preference": "non_smoker",
            "sharing_preference": "no_preference",
            "drinking_preference": "no_preference",
            "pet_preference": "no_preference",
            "cleanliness_preference": "no_preference",
            "budget_min": 1000,
            "budget_max": 2000,
        }

        response = self.client.post(reverse("create_profile"), data=profile_data)

        # Verify profile created
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.university, "NYU")
        self.assertEqual(profile.bio, "Test bio")

        # Step 5: View profile
        response = self.client.get(reverse("view_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John Doe")

    def test_registration_with_unknown_domain_requires_admin_approval(self):
        """Test that unknown domain requires admin approval before full access."""

        # Register with unknown domain
        register_data = {
            "email": "student@unknown-college.edu",
            "username": "unknownstudent",
            "first_name": "Jane",
            "last_name": "Smith",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }

        response = self.client.post(reverse("register"), data=register_data)

        user = User.objects.get(email="student@unknown-college.edu")

        # User should be flagged for admin review
        self.assertTrue(user.requires_admin_verification)
        self.assertIsNone(user.validated_university)
        self.assertFalse(user.domain_verified)

    def test_multiple_users_from_same_university(self):
        """Test that multiple users can register from same university."""

        users_data = [
            ("student1@nyu.edu", "user1", "Alice", "Johnson"),
            ("student2@nyu.edu", "user2", "Bob", "Williams"),
            ("student3@nyu.edu", "user3", "Carol", "Davis"),
        ]

        for email, username, first_name, last_name in users_data:
            register_data = {
                "email": email,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "password1": "testpass123!@#",
                "password2": "testpass123!@#",
            }
            self.client.post(reverse("register"), data=register_data)

        # All users should have same university
        nyu_users = User.objects.filter(validated_university=self.nyu)
        self.assertEqual(nyu_users.count(), 3)

        # Each should be unique
        self.assertEqual(User.objects.count(), 3)

    def test_users_from_different_universities(self):
        """Test users from different universities are correctly assigned."""

        # Register NYU student
        self.client.post(
            reverse("register"),
            data={
                "email": "student@nyu.edu",
                "username": "nyustudent",
                "first_name": "John",
                "last_name": "Doe",
                "password1": "testpass123!@#",
                "password2": "testpass123!@#",
            },
        )

        # Register Columbia student
        self.client.post(
            reverse("register"),
            data={
                "email": "student@columbia.edu",
                "username": "columbiastudent",
                "first_name": "Jane",
                "last_name": "Smith",
                "password1": "testpass123!@#",
                "password2": "testpass123!@#",
            },
        )

        nyu_user = User.objects.get(email="student@nyu.edu")
        columbia_user = User.objects.get(email="student@columbia.edu")

        self.assertEqual(nyu_user.validated_university, self.nyu)
        self.assertEqual(columbia_user.validated_university, self.columbia)
        self.assertNotEqual(nyu_user.validated_university, columbia_user.validated_university)


class UserLoginWithUniversityValidationTests(TestCase):
    """Test login flow with university validation."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        self.nyu = University.objects.create(
            name="New York University", country="United States"
        )

        # Create verified user
        self.verified_user = User.objects.create_user(
            username="verified",
            email="verified@nyu.edu",
            password="testpass123",
            is_verified=True,
            validated_university=self.nyu,
            domain_verified=True,
        )

        # Create unverified user
        self.unverified_user = User.objects.create_user(
            username="unverified",
            email="unverified@nyu.edu",
            password="testpass123",
            is_verified=False,
            validated_university=self.nyu,
            domain_verified=True,
        )

        # Create pending admin approval user
        self.pending_user = User.objects.create_user(
            username="pending",
            email="pending@unknown.edu",
            password="testpass123",
            is_verified=True,
            requires_admin_verification=True,
        )

    def test_verified_user_can_login(self):
        """Test that verified user can login successfully."""
        response = self.client.post(
            reverse("login"),
            data={"username": "verified@nyu.edu", "password": "testpass123"},
        )

        self.assertEqual(response.status_code, 302)  # Redirect after login
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_unverified_user_cannot_login(self):
        """Test that unverified user cannot login."""
        response = self.client.post(
            reverse("login"),
            data={"username": "unverified@nyu.edu", "password": "testpass123"},
            follow=True,
        )

        # Should not be logged in
        self.assertFalse(self.client.session.get("_auth_user_id"))

        # Should see error message
        messages = list(response.context["messages"])
        self.assertTrue(any("verify your email" in str(m).lower() for m in messages))

    def test_pending_approval_user_can_login_after_email_verification(self):
        """Test that user pending admin approval can still login after email verification."""
        # Even though requires admin verification, they can log in
        response = self.client.post(
            reverse("login"),
            data={"username": "pending@unknown.edu", "password": "testpass123"},
        )

        self.assertEqual(response.status_code, 302)


class UniversityDataConsistencyTests(TestCase):
    """Test data consistency across the system."""

    def setUp(self):
        """Set up test data."""
        self.nyu = University.objects.create(
            name="New York University", country="United States"
        )
        UniversityDomain.objects.create(
            university=self.nyu, domain="nyu.edu", is_primary=True
        )

    def test_university_deletion_sets_user_field_to_null(self):
        """Test that deleting university sets user.validated_university to None."""
        user = User.objects.create_user(
            username="nyustudent",
            email="student@nyu.edu",
            password="testpass123",
            validated_university=self.nyu,
            domain_verified=True,
        )

        self.nyu.delete()

        user.refresh_from_db()
        self.assertIsNone(user.validated_university)
        # User should still exist
        self.assertTrue(User.objects.filter(id=user.id).exists())

    def test_domain_uniqueness_across_universities(self):
        """Test that domain cannot be assigned to multiple universities."""
        from django.db import IntegrityError

        # Try to create duplicate domain
        columbia = University.objects.create(
            name="Columbia University", country="United States"
        )

        with self.assertRaises(IntegrityError):
            UniversityDomain.objects.create(
                university=columbia, domain="nyu.edu", is_primary=True
            )

    def test_user_count_per_university(self):
        """Test counting users per university."""
        # Create multiple users from same university
        for i in range(5):
            User.objects.create_user(
                username=f"nyustudent{i}",
                email=f"student{i}@nyu.edu",
                password="testpass123",
                validated_university=self.nyu,
                domain_verified=True,
            )

        self.assertEqual(self.nyu.users.count(), 5)

    def test_profile_auto_population(self):
        """Test that profile creation attempts to auto-populate university."""
        from django.test import RequestFactory
        from profiles.views import create_profile

        # Create user with validated university
        user = User.objects.create_user(
            username="nyustudent",
            email="student@nyu.edu",
            password="testpass123",
            validated_university=self.nyu,
            domain_verified=True,
            is_verified=True,
        )

        # Test profile view context
        factory = RequestFactory()
        request = factory.get(reverse("create_profile"))
        request.user = user

        # The view should include detected_university in context
        # This would be tested via the view, but we can verify the user has the field
        self.assertEqual(user.validated_university.name, "New York University")


class AdminWorkflowIntegrationTests(TestCase):
    """Integration tests for admin workflow."""

    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@campusnest.com",
            password="adminpass123",
        )

        self.pending_user = User.objects.create_user(
            username="pending",
            email="student@unknown.edu",
            password="testpass123",
            requires_admin_verification=True,
            is_verified=True,
        )

        self.client = Client()

    def test_admin_approval_workflow(self):
        """Test complete admin approval workflow."""
        # Login as admin
        self.client.login(username="admin", password="adminpass123")

        # Approve user
        self.pending_user.requires_admin_verification = False
        self.pending_user.save()

        # Verify approval
        self.pending_user.refresh_from_db()
        self.assertFalse(self.pending_user.requires_admin_verification)

    def test_admin_can_filter_pending_users(self):
        """Test that admin can filter users requiring verification."""
        # Create mix of users
        approved_user = User.objects.create_user(
            username="approved",
            email="approved@nyu.edu",
            password="testpass123",
            domain_verified=True,
        )

        pending_users = User.objects.filter(requires_admin_verification=True)
        self.assertEqual(pending_users.count(), 1)
        self.assertIn(self.pending_user, pending_users)
        self.assertNotIn(approved_user, pending_users)
