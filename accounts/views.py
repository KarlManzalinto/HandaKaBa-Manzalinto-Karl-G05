from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .decorators import role_required
from .forms import ProfileUpdateForm, RegisterForm, UserUpdateForm
from .models import Profile


def home(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    return redirect("accounts:login")


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save()  # password is hashed by Django
            login(request, user)
            messages.success(request, "Account created. Welcome to Handa Ka Ba!")
            return redirect("accounts:dashboard")
        messages.error(request, "Registration failed. Please fix the errors below.")
    return render(request, "accounts/register.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().first_name or form.get_user().username}!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)


@login_required
def dashboard(request):
    """Send each user to the dashboard for their role."""
    if request.user.profile.role == Profile.ROLE_ADMIN:
        return redirect("accounts:admin_dashboard")
    return redirect("accounts:household_dashboard")


@role_required(Profile.ROLE_HOUSEHOLD)
def household_dashboard(request):
    return render(request, "dashboards/household.html")


@role_required(Profile.ROLE_ADMIN)
def admin_dashboard(request):
    users = User.objects.select_related("profile").order_by("-date_joined")
    context = {
        "total_users": users.count(),
        "household_count": users.filter(profile__role=Profile.ROLE_HOUSEHOLD).count(),
        "admin_count": users.filter(profile__role=Profile.ROLE_ADMIN).count(),
        "recent_users": users[:10],
    }
    return render(request, "dashboards/admin.html", context)


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html", {"profile_user": request.user})


@login_required
def profile_edit(request):
    user_form = UserUpdateForm(request.POST or None, instance=request.user)
    profile_form = ProfileUpdateForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if request.method == "POST":
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
        messages.error(request, "Could not update profile. Please fix the errors below.")
    return render(request, "accounts/profile_edit.html", {"user_form": user_form, "profile_form": profile_form})
