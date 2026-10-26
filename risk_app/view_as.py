import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.sessions.backends.db import SessionStore
from django.core import signing
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .middleware import SplitSessionMiddleware
from .models import ActivityLog

User = get_user_model()
logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Retrieve client IP address from HTTP headers."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _is_admin(user):
    """Check if the user is an active administrator."""
    return (
        user is not None
        and user.is_authenticated
        and user.is_active
        and (user.is_superuser or (getattr(user, "role", "") == "ADMIN" and user.is_staff))
    )


def _is_valid_target(target, admin_user):
    """Target user must be active, role USER, not staff/superuser, not admin themself."""
    return (
        target is not None
        and target.is_active
        and getattr(target, "role", "") == "USER"
        and not target.is_staff
        and not target.is_superuser
        and target.pk != admin_user.pk
    )


@never_cache
def view_as_enter(request):
    """
    Entry point for the admin view-as hand-off (non-admin URL).
    Validates token, admin session cookie, and target before logging in as target.
    """
    token = request.GET.get("t")
    if not token:
        return HttpResponseForbidden("Missing view-as token.")

    try:
        data = signing.loads(token, salt="rw-view-as", max_age=30)
    except (signing.BadSignature, signing.SignatureExpired):
        return HttpResponseForbidden("Invalid or expired view-as token.")

    admin_pk = data.get("admin")
    target_pk = data.get("target")

    # Read admin cookie value from request.COOKIES using the cookie-name constant used by SplitSessionMiddleware
    cookie_name = SplitSessionMiddleware.ADMIN_COOKIE_NAME
    admin_cookie = request.COOKIES.get(cookie_name)
    if not admin_cookie:
        return HttpResponseForbidden("Admin session cookie missing.")

    admin_session = SessionStore(session_key=admin_cookie)
    auth_user_id = admin_session.get("_auth_user_id")
    if not auth_user_id or str(auth_user_id) != str(admin_pk):
        return HttpResponseForbidden("Admin session verification failed.")

    admin_user = User.objects.filter(pk=auth_user_id).first()
    if not _is_admin(admin_user):
        return HttpResponseForbidden("Admin user is inactive or unauthorized.")

    # Re-validate target
    target = User.objects.filter(pk=target_pk).first()
    if not _is_valid_target(target, admin_user):
        return HttpResponseForbidden("Target user cannot be viewed.")

    # Remember target.last_login, call login(), then restore last_login
    old_last_login = target.last_login
    request._view_as_suppress_login_log = True
    login(request, target, backend="django.contrib.auth.backends.ModelBackend")
    User.objects.filter(pk=target.pk).update(last_login=old_last_login)
    target.last_login = old_last_login

    # Set request.session["view_as_admin_id"] = admin.pk and expiry to 1800 (30 minutes)
    request.session["view_as_admin_id"] = admin_user.pk
    request.session.set_expiry(1800)

    # Activity log
    ActivityLog.objects.create(
        user=admin_user,
        action="Admin view-as started",
        details=f"target user id {target.pk}",
        ip_address=get_client_ip(request),
    )

    return redirect("home")


@never_cache
@require_POST
def view_as_exit(request):
    """
    Exits the view-as session: records ActivityLog, logs out of website session,
    and redirects back to /admin/ (admin session remains intact).
    """
    admin_id = request.session.get("view_as_admin_id")
    admin_user = User.objects.filter(pk=admin_id).first() if admin_id else None

    ActivityLog.objects.create(
        user=admin_user,
        action="Admin view-as ended",
        details=f"admin user id {admin_id}" if admin_id else "",
        ip_address=get_client_ip(request),
    )

    logout(request)
    return redirect("/admin/")
