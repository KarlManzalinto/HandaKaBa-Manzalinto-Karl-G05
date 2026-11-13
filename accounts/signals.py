from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    role = Profile.ROLE_ADMIN if instance.is_superuser else Profile.ROLE_HOUSEHOLD
    profile, was_created = Profile.objects.get_or_create(user=instance, defaults={"role": role})
    if not was_created and instance.is_superuser and profile.role != Profile.ROLE_ADMIN:
        profile.role = Profile.ROLE_ADMIN
        profile.save(update_fields=["role"])
