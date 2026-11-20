from django.contrib import admin

from .models import Category, InventoryItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "per_person_qty", "target_unit", "sort_order")
    ordering = ("sort_order", "name")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "category", "quantity", "unit", "expiry_date")
    list_filter = ("category",)
    search_fields = ("name", "owner__username", "owner__email")
