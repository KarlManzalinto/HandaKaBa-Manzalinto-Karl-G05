from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models


class Profile(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_HOUSEHOLD = "household"
    ROLE_CHOICES = [(ROLE_ADMIN, "Administrator"), (ROLE_HOUSEHOLD, "Household User")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_HOUSEHOLD)
    contact_number = models.CharField(
        max_length=20, blank=True,
        validators=[RegexValidator(r"^\+?[0-9\s\-]{7,15}$", "Enter a valid contact number.")],
    )
    barangay = models.CharField(max_length=100, blank=True)
    household_size = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text="Number of people in your household (used for checklist templates).",
    )
    photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN
