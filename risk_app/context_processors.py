from django.conf import settings


def currency_context(request):
    """Provides CURRENCY_SYMBOL to all Django templates."""
    return {
        "CURRENCY_SYMBOL": getattr(settings, "CURRENCY_SYMBOL", "$"),
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
