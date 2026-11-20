from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

EXPIRY_WARNING_DAYS = 30


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    icon = models.CharField(max_length=8, blank=True)
    description = models.CharField(max_length=160, blank=True)
    per_person_qty = models.PositiveSmallIntegerField(
        default=0,
        help_text="Amount needed per person for a 72-hour kit. Leave 0 if one set covers the whole household.",
    )
    target_unit = models.CharField(max_length=20, default="set")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def target_label(self, household_size):
        if self.per_person_qty:
            return f"{self.per_person_qty * household_size} {self.target_unit}"
        return f"1 {self.target_unit}"


class InventoryQuerySet(models.QuerySet):
    def expired(self):
        return self.filter(expiry_date__lt=timezone.localdate())

    def expiring_soon(self):
        today = timezone.localdate()
        return self.filter(
            expiry_date__gte=today,
            expiry_date__lte=today + timedelta(days=EXPIRY_WARNING_DAYS),
        )

    def needs_attention(self):
        limit = timezone.localdate() + timedelta(days=EXPIRY_WARNING_DAYS)
        return self.filter(expiry_date__isnull=False, expiry_date__lte=limit)

    def good(self):
        limit = timezone.localdate() + timedelta(days=EXPIRY_WARNING_DAYS)
        return self.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gt=limit))


class InventoryItem(models.Model):
    UNIT_CHOICES = [
        ("pcs", "pieces"),
        ("cans", "cans"),
        ("packs", "packs"),
        ("bottles", "bottles"),
        ("liters", "liters"),
        ("boxes", "boxes"),
        ("sets", "sets"),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inventory_items")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(9999)],
    )
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="pcs")
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = InventoryQuerySet.as_manager()

    class Meta:
        ordering = [models.F("expiry_date").asc(nulls_last=True), "name"]

    def __str__(self):
        return f"{self.name} x{self.quantity} ({self.owner})"

    UNIT_SINGULAR = {
        "pcs": "piece",
        "cans": "can",
        "packs": "pack",
        "bottles": "bottle",
        "liters": "liter",
        "boxes": "box",
        "sets": "set",
    }

    @property
    def quantity_label(self):
        if self.quantity == 1:
            return f"1 {self.UNIT_SINGULAR[self.unit]}"
        return f"{self.quantity} {self.get_unit_display()}"

    @property
    def days_left(self):
        if self.expiry_date is None:
            return None
        return (self.expiry_date - timezone.localdate()).days

    @property
    def status(self):
        days = self.days_left
        if days is None:
            return "none"
        if days < 0:
            return "expired"
        if days <= EXPIRY_WARNING_DAYS:
            return "soon"
        return "ok"

    @property
    def status_label(self):
        days = self.days_left
        if days is None:
            return "No expiry"
        if days < 0:
            return "Expired"
        if days == 0:
            return "Expires today"
        if days <= EXPIRY_WARNING_DAYS:
            return f"{days} day{'s' if days != 1 else ''} left"
        return "Good"
