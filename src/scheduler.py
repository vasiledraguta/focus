"""Time-based scheduler for blocking logic."""

from datetime import datetime

from config import ALLOWED_START_HOUR, ALLOWED_END_HOUR


def is_blocking_active() -> bool:
    """
    Check if blocking should be active based on current time.
    
    Blocking is ACTIVE (returns True) when outside the allowed window.
    Blocking is INACTIVE (returns False) during allowed hours.
    Supports overnight windows (e.g., 23:00 to 01:00).
    
    Returns:
        bool: True if sites should be blocked, False if allowed.
    """
    current_hour = datetime.now().hour
    
    if ALLOWED_START_HOUR < ALLOWED_END_HOUR:
        # Same-day window (e.g., 20-22)
        in_allowed_window = ALLOWED_START_HOUR <= current_hour < ALLOWED_END_HOUR
    else:
        # Overnight window (e.g., 23-01)
        in_allowed_window = current_hour >= ALLOWED_START_HOUR or current_hour < ALLOWED_END_HOUR
    
    return not in_allowed_window


def get_status_message() -> str:
    """Get a human-readable status message about blocking state."""
    current_hour = datetime.now().hour
    is_active = is_blocking_active()
    
    if ALLOWED_START_HOUR < ALLOWED_END_HOUR:
        window_str = f"{ALLOWED_START_HOUR:02d}:00 - {ALLOWED_END_HOUR:02d}:00"
    else:
        window_str = f"{ALLOWED_START_HOUR:02d}:00 - {ALLOWED_END_HOUR:02d}:00 (overnight)"
    
    if is_active:
        return (
            f"Blocking is ACTIVE (current hour: {current_hour:02d}:00). "
            f"Sites allowed between {window_str}."
        )
    else:
        return (
            f"Blocking is INACTIVE (current hour: {current_hour:02d}:00). "
            f"You're in the allowed window ({window_str})."
        )
