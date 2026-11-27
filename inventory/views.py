from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import get_role, role_required
from accounts.models import Profile

from .forms import DUPLICATE_MESSAGE, InventoryItemForm
from .models import Category, InventoryItem

PAGE_SIZE = 10
MAX_DB_INT = 2_147_483_647
MAX_SEARCH_LENGTH = 100


def _safe_id(value):
    value = (value or "").strip()
    if value.isdigit() and 0 < int(value) <= MAX_DB_INT:
        return int(value)
    return None


def _filtered(request, queryset, search_fields):
    q = request.GET.get("q", "").replace("\x00", "").strip()[:MAX_SEARCH_LENGTH]
    category = _safe_id(request.GET.get("category"))
    status = request.GET.get("status", "")
    if q:
        condition = Q()
        for field in search_fields:
            condition |= Q(**{f"{field}__icontains": q})
        queryset = queryset.filter(condition)
    if category:
        queryset = queryset.filter(category_id=category)
    if status == "expired":
        queryset = queryset.expired()
    elif status == "soon":
        queryset = queryset.expiring_soon()
    elif status == "ok":
        queryset = queryset.good()
    else:
        status = ""
    return queryset, {"q": q, "category": str(category or ""), "status": status}


def _list_context(request, queryset, search_fields):
    queryset, filters = _filtered(request, queryset, search_fields)
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return {
        "page_obj": page,
        "filters": filters,
        "has_filters": any(filters.values()),
        "querystring": params.urlencode(),
        "categories": Category.objects.all(),
    }


def _visible_item(request, pk):
    queryset = InventoryItem.objects.select_related("category", "owner", "owner__profile")
    if get_role(request.user) != Profile.ROLE_ADMIN:
        queryset = queryset.filter(owner=request.user)
    return get_object_or_404(queryset, pk=pk)


def _save_form(request, form, save):
    """Run save() atomically. Returns True on success, False if the database rejected a duplicate."""
    try:
        with transaction.atomic():
            save()
    except IntegrityError:
        form.add_error("name", DUPLICATE_MESSAGE)
        return False
    return True


@role_required(Profile.ROLE_HOUSEHOLD)
@require_http_methods(["GET", "HEAD"])
def item_list(request):
    queryset = InventoryItem.objects.filter(owner=request.user).select_related("category")
    return render(request, "inventory/list.html", _list_context(request, queryset, ("name", "notes")))


@role_required(Profile.ROLE_HOUSEHOLD)
@require_http_methods(["GET", "HEAD", "POST"])
def item_create(request):
    initial = {}
    category = _safe_id(request.GET.get("category"))
    if category:
        initial["category"] = category
    form = InventoryItemForm(request.POST or None, owner=request.user, initial=initial)
    if request.method == "POST":
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            if _save_form(request, form, item.save):
                messages.success(request, f"{item.name} was added to your go-bag.")
                return redirect("inventory:list")
        messages.error(request, "Could not save the item. Please fix the errors below.")
    return render(request, "inventory/form.html", {
        "form": form,
        "title": "Add item",
        "submit": "Add item",
        "intro": "Log something you've packed so we can watch its expiry date.",
    })


@role_required(Profile.ROLE_HOUSEHOLD)
@require_http_methods(["GET", "HEAD", "POST"])
def item_update(request, pk):
    item = get_object_or_404(InventoryItem.objects.select_related("category"), pk=pk, owner=request.user)
    form = InventoryItemForm(request.POST or None, instance=item, owner=request.user)
    if request.method == "POST":
        if form.is_valid() and _save_form(request, form, form.save):
            messages.success(request, f"{item.name} was updated.")
            return redirect("inventory:detail", pk=item.pk)
        messages.error(request, "Could not update the item. Please fix the errors below.")
    return render(request, "inventory/form.html", {
        "form": form,
        "item": item,
        "title": "Edit item",
        "submit": "Save changes",
        "intro": "Update the quantity or expiry date after you restock.",
    })


@login_required
@require_http_methods(["GET", "HEAD"])
def item_detail(request, pk):
    item = _visible_item(request, pk)
    is_admin = get_role(request.user) == Profile.ROLE_ADMIN
    return render(request, "inventory/detail.html", {
        "item": item,
        "is_admin": is_admin,
        "back_url": "inventory:admin_list" if is_admin else "inventory:list",
    })


@login_required
@require_http_methods(["GET", "HEAD", "POST"])
def item_delete(request, pk):
    item = _visible_item(request, pk)
    is_admin = get_role(request.user) == Profile.ROLE_ADMIN
    destination = "inventory:admin_list" if is_admin else "inventory:list"
    if request.method == "POST":
        name = item.name
        with transaction.atomic():
            item.delete()
        messages.success(request, f"{name} was deleted.")
        return redirect(destination)
    return render(request, "inventory/confirm_delete.html", {"item": item, "is_admin": is_admin, "back_url": destination})


@role_required(Profile.ROLE_ADMIN)
@require_http_methods(["GET", "HEAD"])
def admin_list(request):
    queryset = InventoryItem.objects.select_related("category", "owner", "owner__profile")
    search = ("name", "owner__username", "owner__first_name", "owner__last_name", "owner__profile__barangay")
    return render(request, "inventory/admin_list.html", _list_context(request, queryset, search))
