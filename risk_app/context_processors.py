from django.conf import settings


def currency_context(request):
    """Provides CURRENCY_SYMBOL, SITE_URL, and PLAUSIBLE_DOMAIN to all Django templates."""
    return {
        "CURRENCY_SYMBOL": getattr(settings, "CURRENCY_SYMBOL", "$"),
        "SITE_URL": getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/"),
        "PLAUSIBLE_DOMAIN": getattr(settings, "PLAUSIBLE_DOMAIN", ""),
    }


def view_as_context(request):
    """
    Exposes view_as_admin and the viewed user when the view-as session key exists.
    """
    session = getattr(request, "session", None)
    admin_id = session.get("view_as_admin_id") if session else None
    if not admin_id:
        return {
            "view_as_admin": None,
            "view_as_target": None,
        }

    from .models import User

    admin_user = User.objects.filter(pk=admin_id).first()
    target_user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    return {
        "view_as_admin": admin_user,
        "view_as_target": target_user,
    }
