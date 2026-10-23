from django.conf import settings


def currency_context(request):
    """Provides CURRENCY_SYMBOL to all Django templates."""
    return {
        "CURRENCY_SYMBOL": getattr(settings, "CURRENCY_SYMBOL", "$"),
    }
