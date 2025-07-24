"""
Timezone utility module for Turkey timezone handling.
All datetime operations should use this module to ensure consistent timezone handling.
"""

import pytz
from datetime import datetime
from typing import Optional, Union

# Turkey timezone
TURKEY_TZ = pytz.timezone('Europe/Istanbul')
UTC_TZ = pytz.UTC


def now() -> datetime:
    """
    Get current time in Turkey timezone.
    
    Returns:
        datetime: Current time with Turkey timezone info
    """
    return datetime.now(TURKEY_TZ)


def utc_now() -> datetime:
    """
    Get current UTC time.
    
    Returns:
        datetime: Current time in UTC
    """
    return datetime.now(UTC_TZ)


def to_turkey_time(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert any datetime to Turkey timezone.
    
    Args:
        dt: Datetime object (timezone-aware or naive)
        
    Returns:
        datetime: Datetime in Turkey timezone or None if input is None
    """
    if dt is None:
        return None
    
    # If timezone-naive, assume it's UTC
    if dt.tzinfo is None:
        dt = UTC_TZ.localize(dt)
    
    return dt.astimezone(TURKEY_TZ)


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert any datetime to UTC.
    
    Args:
        dt: Datetime object (timezone-aware or naive)
        
    Returns:
        datetime: Datetime in UTC or None if input is None
    """
    if dt is None:
        return None
    
    # If timezone-naive, assume it's Turkey time
    if dt.tzinfo is None:
        dt = TURKEY_TZ.localize(dt)
    
    return dt.astimezone(UTC_TZ)


def format_for_display(dt: Optional[datetime], format_str: str = "%d.%m.%Y %H:%M:%S") -> str:
    """
    Format datetime for display in Turkey timezone.
    
    Args:
        dt: Datetime object
        format_str: Format string
        
    Returns:
        str: Formatted datetime string or empty string if None
    """
    if dt is None:
        return ""
    
    turkey_time = to_turkey_time(dt)
    return turkey_time.strftime(format_str)


def format_for_web(dt: Optional[datetime]) -> str:
    """
    Format datetime for web display (ISO format in Turkey timezone).
    
    Args:
        dt: Datetime object
        
    Returns:
        str: ISO formatted datetime string in Turkey timezone
    """
    if dt is None:
        return ""
    
    turkey_time = to_turkey_time(dt)
    return turkey_time.isoformat()


def parse_datetime(date_string: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse datetime string assuming Turkey timezone.
    
    Args:
        date_string: Datetime string
        format_str: Format string
        
    Returns:
        datetime: Timezone-aware datetime in Turkey timezone
    """
    dt = datetime.strptime(date_string, format_str)
    return TURKEY_TZ.localize(dt)


def get_day_start(dt: Optional[datetime] = None) -> datetime:
    """
    Get start of day in Turkey timezone.
    
    Args:
        dt: Reference datetime (default: now)
        
    Returns:
        datetime: Start of day in Turkey timezone
    """
    if dt is None:
        dt = now()
    else:
        dt = to_turkey_time(dt)
    
    return TURKEY_TZ.localize(datetime(dt.year, dt.month, dt.day, 0, 0, 0))


def get_day_end(dt: Optional[datetime] = None) -> datetime:
    """
    Get end of day in Turkey timezone.
    
    Args:
        dt: Reference datetime (default: now)
        
    Returns:
        datetime: End of day in Turkey timezone
    """
    if dt is None:
        dt = now()
    else:
        dt = to_turkey_time(dt)
    
    return TURKEY_TZ.localize(datetime(dt.year, dt.month, dt.day, 23, 59, 59, 999999))


# For backward compatibility
def get_turkey_time() -> datetime:
    """Deprecated: Use now() instead."""
    return now()