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


def parse_datetime(date_string: str, format_str: str = None) -> datetime:
    """
    Parse datetime string assuming Turkey timezone.
    
    Args:
        date_string: Datetime string
        format_str: Format string (if None, tries common formats)
        
    Returns:
        datetime: Timezone-aware datetime in Turkey timezone
    """
    if format_str:
        dt = datetime.strptime(date_string, format_str)
    else:
        # Try common formats
        formats = [
            "%Y-%m-%d %H:%M:%S.%f",  # With microseconds
            "%Y-%m-%d %H:%M:%S",      # Without microseconds
            "%Y-%m-%dT%H:%M:%S.%f",   # ISO format with microseconds
            "%Y-%m-%dT%H:%M:%S",      # ISO format without microseconds
        ]
        
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(date_string, fmt)
                break
            except ValueError:
                continue
        
        if dt is None:
            raise ValueError(f"Unable to parse datetime string: {date_string}")
    
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


def parse_timestamp(timestamp_str: Union[str, datetime]) -> datetime:
    """
    Parse timestamp string or datetime object to Turkey timezone.
    
    Args:
        timestamp_str: Timestamp string or datetime object
        
    Returns:
        datetime: Timezone-aware datetime in Turkey timezone
    """
    if isinstance(timestamp_str, datetime):
        return to_turkey_time(timestamp_str)
    
    # Try different formats
    formats = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_str, fmt)
            # If no timezone info, assume UTC
            if dt.tzinfo is None:
                dt = UTC_TZ.localize(dt)
            return dt.astimezone(TURKEY_TZ)
        except ValueError:
            continue
    
    # If none worked, try with dateutil parser as fallback
    try:
        from dateutil.parser import parse
        dt = parse(timestamp_str)
        if dt.tzinfo is None:
            dt = UTC_TZ.localize(dt)
        return dt.astimezone(TURKEY_TZ)
    except (ImportError, ValueError):
        pass
    
    raise ValueError(f"Could not parse timestamp: {timestamp_str}")


# For backward compatibility
def get_turkey_time() -> datetime:
    """Deprecated: Use now() instead."""
    return now()