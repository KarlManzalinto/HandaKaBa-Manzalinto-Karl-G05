from django import forms
from django.utils import timezone

from .models import Category, InventoryItem

DUPLICATE_MESSAGE = "You already have this item in that category. Edit it to change the quantity."


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ("category", "name", "quantity", "unit", "expiry_date", "notes")
        widgets = {
            "expiry_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3, "maxlength": 255}),
            "quantity": forms.NumberInput(attrs={"min": 1, "max": 9999}),
            "name": forms.TextInput(attrs={"placeholder": "e.g. Canned sardines"}),
        }
        help_texts = {
            "expiry_date": "Leave blank for items that don't expire, like a flashlight.",
        }

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].empty_label = "Choose a category"

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if len(name) < 2:
            raise forms.ValidationError("Item name must be at least 2 characters.")
        return name

    def clean_notes(self):
        return " ".join(self.cleaned_data["notes"].split())

    def clean_expiry_date(self):
        expiry = self.cleaned_data.get("expiry_date")
        if expiry and expiry < timezone.localdate():
            unchanged = self.instance.pk and expiry == self.instance.expiry_date
            if not unchanged:
                raise forms.ValidationError("Expiry date can't be in the past. Don't pack items that are already expired.")
        return expiry

    def clean(self):
        cleaned = super().clean()
        name, category = cleaned.get("name"), cleaned.get("category")
        if self.owner and name and category:
            duplicates = InventoryItem.objects.filter(owner=self.owner, category=category, name__iexact=name)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error("name", DUPLICATE_MESSAGE)
        return cleaned
