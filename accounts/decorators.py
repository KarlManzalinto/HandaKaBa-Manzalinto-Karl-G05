from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import Profile


def get_role(user):
    profile = getattr(user, "profile", None)
    if profile is None:
        default_role = Profile.ROLE_ADMIN if user.is_superuser else Profile.ROLE_HOUSEHOLD
        profile, _ = Profile.objects.get_or_create(user=user, defaults={"role": default_role})
    return profile.role


def role_required(role):
    """Login required + user must have the given role; otherwise bounce to own dashboard."""
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if get_role(request.user) != role:
                messages.error(request, "You don't have permission to open that page.")
                return redirect("accounts:dashboard")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator
