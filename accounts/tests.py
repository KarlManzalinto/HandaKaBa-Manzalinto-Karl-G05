import io
import os

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .models import Profile

PASSWORD = "Str0ng!Pass#77"


def png_upload(name="photo.png", size=(20, 20), fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, "teal").save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")


def registration_data(**overrides):
    data = {
        "username": "juan", "first_name": "Juan", "last_name": "Cruz", "email": "juan@example.com",
        "password1": PASSWORD, "password2": PASSWORD,
    }
    data.update(overrides)
    return data


class RegistrationTests(TestCase):
    def test_valid_registration_creates_hashed_household_user_and_logs_in(self):
        response = self.client.post(reverse("accounts:register"), registration_data(), follow=True)
        user = User.objects.get(username="juan")
        self.assertNotIn(PASSWORD, user.password)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertIn("$", user.password)
        self.assertEqual(user.profile.role, Profile.ROLE_HOUSEHOLD)
        self.assertContains(response, "Account created")
        self.assertEqual(response.context["user"], user)

    def test_invalid_registrations_are_rejected_with_error_message(self):
        User.objects.create_user("taken", "taken@example.com", PASSWORD)
        bad_inputs = [
            {"email": "not-an-email"},
            {"email": ""},
            {"first_name": ""},
            {"last_name": ""},
            {"password2": "different"},
            {"username": "taken"},
            {"username": "TAKEN"},
            {"email": "TAKEN@example.com"},
            {"password1": "12345678", "password2": "12345678"},
        ]
        for overrides in bad_inputs:
            response = self.client.post(reverse("accounts:register"), registration_data(**overrides))
            self.assertEqual(response.status_code, 200, overrides)
            self.assertContains(response, "Registration failed", msg_prefix=str(overrides))
        self.assertEqual(User.objects.count(), 1)

    def test_role_cannot_be_chosen_during_registration(self):
        self.client.post(reverse("accounts:register"), registration_data(role="admin", is_superuser="on"))
        user = User.objects.get(username="juan")
        self.assertEqual(user.profile.role, Profile.ROLE_HOUSEHOLD)
        self.assertFalse(user.is_superuser)

    def test_password_help_text_is_rendered_as_html_not_escaped(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertNotContains(response, "&lt;ul&gt;")


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ana", "ana@example.com", PASSWORD, first_name="Ana")
        self.admin = User.objects.create_superuser("boss", "boss@example.com", PASSWORD)

    def test_invalid_login_shows_one_clear_error(self):
        response = self.client.post(reverse("accounts:login"), {"username": "ana", "password": "wrong"})
        self.assertContains(response, "Invalid username or password.", count=1)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_each_role_lands_on_its_own_dashboard(self):
        self.client.post(reverse("accounts:login"), {"username": "ana", "password": PASSWORD})
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertRedirects(response, reverse("accounts:household_dashboard"))
        self.client.logout()
        self.client.post(reverse("accounts:login"), {"username": "boss", "password": PASSWORD})
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertRedirects(response, reverse("accounts:admin_dashboard"))

    def test_logout_requires_post_and_ends_session(self):
        self.client.login(username="ana", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        response = self.client.post(reverse("accounts:logout"), follow=True)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "You have been logged out.")

    def test_logged_out_users_are_sent_to_login(self):
        for name in ("dashboard", "household_dashboard", "admin_dashboard", "profile", "profile_edit"):
            response = self.client.get(reverse(f"accounts:{name}"))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn(reverse("accounts:login"), response["Location"], name)

    def test_login_does_not_redirect_to_other_sites(self):
        response = self.client.post(
            reverse("accounts:login") + "?next=https://evil.example/", {"username": "ana", "password": PASSWORD}
        )
        self.assertNotIn("evil.example", response["Location"])

    def test_users_cannot_open_the_other_roles_dashboard(self):
        self.client.login(username="ana", password=PASSWORD)
        response = self.client.get(reverse("accounts:admin_dashboard"), follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:household_dashboard"))
        self.assertContains(response, "don&#x27;t have permission")
        self.client.logout()
        self.client.login(username="boss", password=PASSWORD)
        response = self.client.get(reverse("accounts:household_dashboard"), follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:admin_dashboard"))

    def test_user_without_profile_row_does_not_crash(self):
        Profile.objects.filter(user=self.user).delete()
        self.client.login(username="ana", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("accounts:household_dashboard")).status_code, 200)


class ProfileTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", "ana@example.com", PASSWORD, first_name="Ana", last_name="Reyes")
        self.ben = User.objects.create_user("ben", "ben@example.com", PASSWORD, first_name="Ben", last_name="Cruz")
        self.client.login(username="ana", password=PASSWORD)
        self.url = reverse("accounts:profile_edit")

    def payload(self, **overrides):
        data = {"first_name": "Ana", "last_name": "Reyes", "email": "ana@example.com",
                "contact_number": "0917 123 4567", "barangay": "  Lahug  ", "household_size": 4}
        data.update(overrides)
        return data

    def test_profile_page_shows_only_own_data(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "Ana")
        self.assertNotContains(response, "ben@example.com")

    def test_valid_update_is_saved(self):
        response = self.client.post(self.url, self.payload(), follow=True)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.profile.barangay, "Lahug")
        self.assertEqual(self.ana.profile.household_size, 4)
        self.assertContains(response, "Profile updated successfully")

    def test_invalid_updates_are_rejected(self):
        for overrides in ({"email": "bad"}, {"email": "ben@example.com"}, {"contact_number": "abc"},
                          {"household_size": 0}, {"household_size": 99}, {"first_name": ""}):
            response = self.client.post(self.url, self.payload(**overrides))
            self.assertContains(response, "Could not update profile", msg_prefix=str(overrides))

    def test_update_is_all_or_nothing(self):
        self.client.post(self.url, self.payload(first_name="Changed", household_size=99))
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.first_name, "Ana")

    def test_role_cannot_be_changed_by_tampering(self):
        self.client.post(self.url, self.payload(role="admin"))
        self.ana.profile.refresh_from_db()
        self.assertEqual(self.ana.profile.role, Profile.ROLE_HOUSEHOLD)

    def test_photo_must_be_small_image_of_allowed_type(self):
        fake = SimpleUploadedFile("evil.png", b"not really an image", content_type="image/png")
        response = self.client.post(self.url, {**self.payload(), "photo": fake})
        self.assertContains(response, "Could not update profile")
        gif = png_upload("x.gif", fmt="GIF")
        response = self.client.post(self.url, {**self.payload(), "photo": gif})
        self.assertContains(response, "JPEG, PNG or WebP")
        noise = Image.frombytes("RGB", (1000, 1000), os.urandom(1000 * 1000 * 3))
        buffer = io.BytesIO()
        noise.save(buffer, "PNG")
        big = SimpleUploadedFile("big.png", buffer.getvalue(), content_type="image/png")
        self.assertGreater(len(buffer.getvalue()), 2 * 1024 * 1024)
        response = self.client.post(self.url, {**self.payload(), "photo": big})
        self.assertContains(response, "2 MB or smaller")

    def test_valid_photo_upload_works(self):
        import shutil
        import tempfile
        from django.test import override_settings
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            response = self.client.post(self.url, {**self.payload(), "photo": png_upload()}, follow=True)
            self.assertContains(response, "Profile updated successfully")
            self.ana.profile.refresh_from_db()
            self.assertTrue(self.ana.profile.photo.name.startswith("profile_photos/"))
