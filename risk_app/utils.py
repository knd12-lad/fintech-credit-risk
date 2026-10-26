def needle_angle(score):
    """
    Calculate gauge needle rotation angle (0 to 180 degrees) from credit score (300 to 900).
    Formula: clamp((score - 300) * 0.3, 0, 180), rounded to 1 decimal.
    """
    try:
        val = (float(score) - 300.0) * 0.3
    except (TypeError, ValueError):
        val = 0.0
    clamped = max(0.0, min(180.0, val))
    return round(clamped, 1)
