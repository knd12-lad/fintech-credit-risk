from django.conf import settings


def currency_context(request):
    """Provides CURRENCY_SYMBOL, SITE_URL, and PLAUSIBLE_DOMAIN to all Django templates."""
    return {
        "CURRENCY_SYMBOL": getattr(settings, "CURRENCY_SYMBOL", "$"),
        "SITE_URL": getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/"),
        "PLAUSIBLE_DOMAIN": getattr(settings, "PLAUSIBLE_DOMAIN", ""),
    }


def is_read_only_session(request):
    """
    Check if the current session is read-only (admin view-as or demo mode).
    """
    session = getattr(request, "session", None)
    if not session:
        return False
    if session.get("view_as_admin_id"):
        return True
    if session.get("is_demo_mode") or getattr(request, "is_demo_mode", False):
        return True
    return False


def view_as_context(request):
    """
    Exposes view_as_admin, view_as_target, and is_read_only when the view-as session key exists.
    """
    session = getattr(request, "session", None)
    admin_id = session.get("view_as_admin_id") if session else None
    read_only = is_read_only_session(request)

    if not admin_id:
        return {
            "view_as_admin": None,
            "view_as_target": None,
            "is_read_only": read_only,
            "is_read_only_session": read_only,
        }

    from .models import User

    admin_user = User.objects.filter(pk=admin_id).first()
    target_user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    return {
        "view_as_admin": admin_user,
        "view_as_target": target_user,
        "is_read_only": read_only,
        "is_read_only_session": read_only,
    }

