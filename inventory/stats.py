from django.db.models import Count

from .models import Category, InventoryItem


def household_summary(user):
    items = InventoryItem.objects.filter(owner=user)
    counts = dict(items.order_by().values_list("category_id").annotate(n=Count("id")))
    size = user.profile.household_size
    categories = list(Category.objects.all())
    covered = sum(1 for c in categories if counts.get(c.pk))
    attention = items.needs_attention().select_related("category").order_by("expiry_date")[:5]
    return {
        "total_items": items.count(),
        "categories_total": len(categories),
        "categories_covered": covered,
        "readiness_pct": round(covered * 100 / len(categories)) if categories else 0,
        "expiring_soon": items.expiring_soon().count(),
        "expired": items.expired().count(),
        "attention_items": attention,
        "checklist": [
            {
                "pk": c.pk,
                "icon": c.icon,
                "name": c.name,
                "description": c.description,
                "target": c.target_label(size),
                "count": counts.get(c.pk, 0),
            }
            for c in categories
        ],
    }


def overall_summary():
    items = InventoryItem.objects.all()
    return {
        "total_items": items.count(),
        "households_with_items": items.order_by().values("owner").distinct().count(),
        "expiring_soon": items.expiring_soon().count(),
        "expired": items.expired().count(),
    }
