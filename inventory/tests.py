from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, InventoryItem


def make_user(username, superuser=False):
    if superuser:
        return User.objects.create_superuser(username, f"{username}@example.com", "Pass12345!x")
    return User.objects.create_user(username, f"{username}@example.com", "Pass12345!x", first_name=username.title())


class InventoryTestBase(TestCase):
    def setUp(self):
        self.ana = make_user("ana")
        self.ben = make_user("ben")
        self.boss = make_user("boss", superuser=True)
        self.water = Category.objects.get(name="Drinking water")
        self.food = Category.objects.get(name="Ready-to-eat food")
        self.today = timezone.localdate()

    def item(self, owner=None, **kwargs):
        data = dict(owner=owner or self.ana, category=self.water, name="Bottled water", quantity=6, unit="bottles")
        data.update(kwargs)
        return InventoryItem.objects.create(**data)

    def payload(self, **kwargs):
        data = dict(category=self.water.pk, name="Canned tuna", quantity=4, unit="cans",
                    expiry_date=(self.today + timedelta(days=200)).isoformat(), notes="")
        data.update(kwargs)
        return data

    def login(self, user):
        self.client.login(username=user.username, password="Pass12345!x")


class AccessTests(InventoryTestBase):
    def test_login_required_everywhere(self):
        item = self.item()
        for name, args in [("list", []), ("add", []), ("admin_list", []), ("detail", [item.pk]),
                           ("edit", [item.pk]), ("delete", [item.pk])]:
            response = self.client.get(reverse(f"inventory:{name}", args=args))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn("/login/", response["Location"], name)

    def test_categories_are_seeded(self):
        self.assertEqual(Category.objects.count(), 5)

    def test_admin_cannot_use_household_pages(self):
        self.login(self.boss)
        item = self.item()
        for name, args in [("list", []), ("add", []), ("edit", [item.pk])]:
            response = self.client.get(reverse(f"inventory:{name}", args=args))
            self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)

    def test_household_cannot_open_admin_list(self):
        self.login(self.ana)
        response = self.client.get(reverse("inventory:admin_list"))
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)


class CrudTests(InventoryTestBase):
    def test_create_links_item_to_logged_in_user(self):
        self.login(self.ana)
        response = self.client.post(reverse("inventory:add"), self.payload(), follow=True)
        item = InventoryItem.objects.get(name="Canned tuna")
        self.assertEqual(item.owner, self.ana)
        self.assertContains(response, "was added to your go-bag")

    def test_read_shows_only_own_items(self):
        self.item(self.ana, name="Ana water")
        self.item(self.ben, name="Ben water")
        self.login(self.ana)
        response = self.client.get(reverse("inventory:list"))
        self.assertContains(response, "Ana water")
        self.assertNotContains(response, "Ben water")

    def test_update_own_item(self):
        item = self.item()
        self.login(self.ana)
        response = self.client.post(reverse("inventory:edit", args=[item.pk]),
                                    self.payload(name="Bottled water", quantity=12), follow=True)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 12)
        self.assertContains(response, "was updated")

    def test_delete_own_item(self):
        item = self.item()
        self.login(self.ana)
        self.assertEqual(self.client.get(reverse("inventory:delete", args=[item.pk])).status_code, 200)
        response = self.client.post(reverse("inventory:delete", args=[item.pk]), follow=True)
        self.assertFalse(InventoryItem.objects.filter(pk=item.pk).exists())
        self.assertContains(response, "was deleted")

    def test_delete_needs_post(self):
        item = self.item()
        self.login(self.ana)
        self.client.get(reverse("inventory:delete", args=[item.pk]))
        self.assertTrue(InventoryItem.objects.filter(pk=item.pk).exists())


class OwnershipTests(InventoryTestBase):
    def test_other_household_gets_404(self):
        item = self.item(self.ana)
        self.login(self.ben)
        for name in ("detail", "edit", "delete"):
            self.assertEqual(self.client.get(reverse(f"inventory:{name}", args=[item.pk])).status_code, 404, name)
        self.client.post(reverse("inventory:delete", args=[item.pk]))
        self.client.post(reverse("inventory:edit", args=[item.pk]), self.payload(name="Hacked"))
        item.refresh_from_db()
        self.assertEqual(item.name, "Bottled water")

    def test_admin_can_view_and_delete_any_item_but_not_edit(self):
        item = self.item(self.ana)
        self.login(self.boss)
        self.assertContains(self.client.get(reverse("inventory:admin_list")), "Bottled water")
        self.assertEqual(self.client.get(reverse("inventory:detail", args=[item.pk])).status_code, 200)
        self.client.post(reverse("inventory:edit", args=[item.pk]), self.payload(name="Changed"))
        item.refresh_from_db()
        self.assertEqual(item.name, "Bottled water")
        self.client.post(reverse("inventory:delete", args=[item.pk]))
        self.assertFalse(InventoryItem.objects.filter(pk=item.pk).exists())


class ValidationTests(InventoryTestBase):
    def post_add(self, **kwargs):
        self.login(self.ana)
        return self.client.post(reverse("inventory:add"), self.payload(**kwargs))

    def test_required_fields(self):
        for field in ("category", "name", "quantity", "unit"):
            response = self.post_add(**{field: ""})
            self.assertEqual(response.status_code, 200, field)
        self.assertEqual(InventoryItem.objects.count(), 0)

    def test_quantity_must_be_at_least_one(self):
        self.post_add(quantity=0)
        self.post_add(quantity=-3)
        self.post_add(quantity="abc")
        self.assertEqual(InventoryItem.objects.count(), 0)

    def test_past_expiry_rejected_on_create(self):
        response = self.post_add(expiry_date=(self.today - timedelta(days=1)).isoformat())
        self.assertContains(response, "can&#x27;t be in the past")
        self.assertEqual(InventoryItem.objects.count(), 0)

    def test_expiry_is_optional(self):
        self.post_add(expiry_date="")
        self.assertIsNone(InventoryItem.objects.get().expiry_date)

    def test_duplicate_name_in_category_rejected(self):
        self.item(name="Canned tuna")
        response = self.post_add(name="canned TUNA")
        self.assertContains(response, "already have this item")
        self.assertEqual(InventoryItem.objects.count(), 1)

    def test_same_name_allowed_for_other_household(self):
        self.item(self.ben, name="Canned tuna")
        self.post_add(name="Canned tuna")
        self.assertEqual(InventoryItem.objects.count(), 2)

    def test_already_expired_item_can_still_be_edited(self):
        item = self.item(expiry_date=self.today - timedelta(days=5))
        self.login(self.ana)
        self.client.post(reverse("inventory:edit", args=[item.pk]),
                         self.payload(name="Bottled water", expiry_date=item.expiry_date.isoformat(), quantity=9))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 9)

    def test_short_name_rejected(self):
        self.post_add(name="a")
        self.assertEqual(InventoryItem.objects.count(), 0)


class StatusAndDashboardTests(InventoryTestBase):
    def test_status_labels(self):
        self.assertEqual(self.item(name="a1", expiry_date=self.today - timedelta(days=1)).status, "expired")
        self.assertEqual(self.item(name="a2", expiry_date=self.today + timedelta(days=10)).status, "soon")
        self.assertEqual(self.item(name="a3", expiry_date=self.today + timedelta(days=90)).status, "ok")
        self.assertEqual(self.item(name="a4").status, "none")

    def test_filters(self):
        self.item(name="Old milk", expiry_date=self.today - timedelta(days=2))
        self.item(name="Fresh rice", category=self.food, expiry_date=self.today + timedelta(days=300))
        self.login(self.ana)
        url = reverse("inventory:list")
        self.assertContains(self.client.get(url, {"status": "expired"}), "Old milk")
        self.assertNotContains(self.client.get(url, {"status": "expired"}), "Fresh rice")
        self.assertNotContains(self.client.get(url, {"category": self.food.pk}), "Old milk")
        self.assertContains(self.client.get(url, {"q": "rice"}), "Fresh rice")

    def test_household_dashboard_uses_real_data(self):
        self.item(expiry_date=self.today + timedelta(days=5))
        self.item(category=self.food, name="Crackers")
        self.login(self.ana)
        response = self.client.get(reverse("accounts:household_dashboard"))
        self.assertEqual(response.context["total_items"], 2)
        self.assertEqual(response.context["categories_covered"], 2)
        self.assertEqual(response.context["readiness_pct"], 40)
        self.assertEqual(response.context["expiring_soon"], 1)

    def test_admin_dashboard_shows_inventory_totals(self):
        self.item(self.ana)
        self.item(self.ben, name="Ben water")
        self.login(self.boss)
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.context["inventory"]["total_items"], 2)
        self.assertEqual(response.context["inventory"]["households_with_items"], 2)

    def test_deleting_user_removes_their_items(self):
        self.item(self.ana)
        self.ana.delete()
        self.assertEqual(InventoryItem.objects.count(), 0)


class DataIntegrityTests(InventoryTestBase):
    def test_database_rejects_duplicate_item_even_if_form_is_bypassed(self):
        self.item(name="Canned tuna")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.item(name="CANNED TUNA")

    def test_database_rejects_zero_or_huge_quantity(self):
        for quantity in (0, 10000):
            with self.assertRaises(IntegrityError), transaction.atomic():
                self.item(name=f"Bad {quantity}", quantity=quantity)

    def test_category_in_use_cannot_be_deleted(self):
        from django.db.models import ProtectedError
        self.item()
        with self.assertRaises(ProtectedError):
            self.water.delete()

    def test_double_submit_creates_only_one_record(self):
        self.login(self.ana)
        for _ in range(2):
            self.client.post(reverse("inventory:add"), self.payload())
        self.assertEqual(InventoryItem.objects.filter(owner=self.ana, name="Canned tuna").count(), 1)

    def test_successful_post_redirects_so_refresh_does_not_resubmit(self):
        self.login(self.ana)
        response = self.client.post(reverse("inventory:add"), self.payload())
        self.assertEqual(response.status_code, 302)

    def test_http_methods_are_restricted(self):
        item = self.item()
        self.login(self.ana)
        self.assertEqual(self.client.put(reverse("inventory:delete", args=[item.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse("inventory:list")).status_code, 405)
        self.assertEqual(self.client.post(reverse("inventory:detail", args=[item.pk])).status_code, 405)
        self.assertTrue(InventoryItem.objects.filter(pk=item.pk).exists())

    def test_whitespace_is_cleaned_from_text_fields(self):
        self.login(self.ana)
        self.client.post(reverse("inventory:add"), self.payload(name="  Canned    tuna  ", notes="  keep   dry "))
        item = InventoryItem.objects.get()
        self.assertEqual((item.name, item.notes), ("Canned tuna", "keep dry"))
