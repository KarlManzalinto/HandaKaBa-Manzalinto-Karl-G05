from django.db import migrations

CATEGORIES = [
    ("Drinking water", "\U0001F4A7", "3 liters per person per day", 9, "L", 1),
    ("Ready-to-eat food", "\U0001F96B", "Canned goods, biscuits, instant meals", 9, "meals", 2),
    ("Medicine and first aid", "\U0001F48A", "Maintenance meds, bandages, antiseptic", 0, "kit", 3),
    ("Flashlight and batteries", "\U0001F50B", "Plus a power bank and a whistle", 0, "set", 4),
    ("IDs and documents", "\U0001F4C4", "In a waterproof pouch, with some cash", 0, "pouch", 5),
]


def seed(apps, schema_editor):
    Category = apps.get_model("inventory", "Category")
    for name, icon, description, per_person, unit, order in CATEGORIES:
        Category.objects.get_or_create(
            name=name,
            defaults={
                "icon": icon,
                "description": description,
                "per_person_qty": per_person,
                "target_unit": unit,
                "sort_order": order,
            },
        )


def unseed(apps, schema_editor):
    Category = apps.get_model("inventory", "Category")
    Category.objects.filter(name__in=[c[0] for c in CATEGORIES], items__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
