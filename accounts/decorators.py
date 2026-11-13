from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(role):
    """Login required + user must have the given role; otherwise bounce to own dashboard."""
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.profile.role != role:
                messages.error(request, "You don't have permission to open that page.")
                return redirect("accounts:dashboard")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator
