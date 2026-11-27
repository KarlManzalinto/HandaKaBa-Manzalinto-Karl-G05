import pathlib
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.views.defaults import server_error

from inventory.models import Category, InventoryItem

PASSWORD = "Str0ng!Pass#77"


class ErrorPageTests(TestCase):
    def test_unknown_url_shows_custom_404_not_debug_page(self):
        response = self.client.get("/this/page/does/not/exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)
        self.assertNotContains(response, "Using the URLconf", status_code=404)
        self.assertNotContains(response, "Traceback", status_code=404)

    def test_500_page_is_custom_and_leaks_nothing(self):
        response = server_error(RequestFactory().get("/"))
        body = response.content.decode()
        self.assertEqual(response.status_code, 500)
        self.assertIn("Something went wrong on our side", body)
        self.assertNotIn("Traceback", body)

    def test_debug_is_off_during_tests_and_controlled_by_env(self):
        self.assertFalse(settings.DEBUG)
        source = (pathlib.Path(settings.BASE_DIR) / "handakaba" / "settings.py").read_text()
        self.assertIn('env_bool("DJANGO_DEBUG"', source)
        self.assertIn('os.environ.get("DJANGO_SECRET_KEY"', source)

    def test_missing_csrf_token_gets_friendly_403(self):
        User.objects.create_user("ana", "ana@example.com", PASSWORD)
        strict = Client(enforce_csrf_checks=True)
        strict.login(username="ana", password=PASSWORD)
        response = strict.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Your session expired", status_code=403)

    def test_invalid_inventory_ids_return_404_not_500(self):
        User.objects.create_user("ana", "ana@example.com", PASSWORD)
        self.client.login(username="ana", password=PASSWORD)
        for pk in ("0", "999999", "99999999999999999999999"):
            for route in ("detail", "edit", "delete"):
                response = self.client.get(f"/inventory/{pk}/" + {"detail": "", "edit": "edit/", "delete": "delete/"}[route])
                self.assertEqual(response.status_code, 404, (pk, route))
        self.assertEqual(self.client.get("/inventory/abc/").status_code, 404)


class SecurityTests(TestCase):
    def test_security_headers_present(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_session_cookie_is_http_only(self):
        User.objects.create_user("ana", "ana@example.com", PASSWORD)
        self.client.post(reverse("accounts:login"), {"username": "ana", "password": PASSWORD})
        self.assertTrue(self.client.cookies[settings.SESSION_COOKIE_NAME]["httponly"])

    def test_every_post_form_has_a_csrf_token(self):
        User.objects.create_user("ana", "ana@example.com", PASSWORD)
        for name in ("accounts:login", "accounts:register"):
            self.assertContains(self.client.get(reverse(name)), "csrfmiddlewaretoken")
        self.client.login(username="ana", password=PASSWORD)
        item = InventoryItem.objects.create(
            owner=User.objects.get(username="ana"), category=Category.objects.first(), name="Rice", quantity=2
        )
        for url in (reverse("inventory:add"), reverse("inventory:edit", args=[item.pk]),
                    reverse("inventory:delete", args=[item.pk]), reverse("accounts:profile_edit"),
                    reverse("accounts:household_dashboard")):
            self.assertContains(self.client.get(url), "csrfmiddlewaretoken", msg_prefix=url)

    def test_templates_never_mark_content_safe_or_use_raw_sql(self):
        root = pathlib.Path(settings.BASE_DIR)
        for path in list(root.glob("**/*.html")) + list(root.glob("**/*.py")):
            if any(part in ("venv", ".git", "migrations") for part in path.parts) or path.name == "tests.py":
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\|\s*safe\b", str(path))
            self.assertNotIn("mark_safe", text, str(path))
            self.assertNotRegex(text, r"\.raw\(|cursor\(\)|\.extra\(", str(path))
            self.assertNotIn("csrf_exempt", text, str(path))

    def test_user_input_is_escaped_in_pages(self):
        user = User.objects.create_user("ana", "ana@example.com", PASSWORD, first_name="<script>alert(1)</script>")
        InventoryItem.objects.create(owner=user, category=Category.objects.first(), name="<b>bold</b>", quantity=1)
        self.client.login(username="ana", password=PASSWORD)
        for url in (reverse("inventory:list"), reverse("accounts:household_dashboard")):
            body = self.client.get(url).content.decode()
            self.assertNotIn("<script>alert(1)</script>", body)
            self.assertNotIn("<b>bold</b>", body)

    def test_hostile_query_strings_do_not_crash_lists(self):
        User.objects.create_user("ana", "ana@example.com", PASSWORD)
        self.client.login(username="ana", password=PASSWORD)
        for query in ("?category=99999999999999999999", "?page=-5", "?page=abc", "?q=%00", "?status=%27%3B--",
                      "?category=-1&q=" + "a" * 5000, "?page=999999"):
            self.assertEqual(self.client.get(reverse("inventory:list") + query).status_code, 200, query)


class QueryEfficiencyTests(TestCase):
    def test_list_pages_do_not_run_extra_queries_per_row(self):
        owner = User.objects.create_user("ana", "ana@example.com", PASSWORD)
        boss = User.objects.create_superuser("boss", "boss@example.com", PASSWORD)
        categories = list(Category.objects.all())

        def add_items(count, start):
            for i in range(count):
                InventoryItem.objects.create(owner=owner, category=categories[i % 5], name=f"Item {start + i}", quantity=1)

        def queries_for(client, url):
            with CaptureQueriesContext(connection) as ctx:
                client.get(url)
            return len(ctx)

        household, admin = Client(), Client()
        household.login(username="ana", password=PASSWORD)
        admin.login(username="boss", password=PASSWORD)
        add_items(2, 0)
        small = (queries_for(household, reverse("inventory:list")), queries_for(admin, reverse("inventory:admin_list")))
        add_items(8, 2)
        large = (queries_for(household, reverse("inventory:list")), queries_for(admin, reverse("inventory:admin_list")))
        self.assertEqual(small, large)
