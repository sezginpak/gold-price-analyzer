"""
Web utility modulleri
"""

from .cache import CacheManager
from .stats import StatsManager
from .formatters import format_analysis_summary, parse_log_line

# Optimized cache with 10 minute default TTL and 2000 max entries
cache = CacheManager(default_ttl=600, max_entries=2000)
stats = StatsManager()

__all__ = [
    'cache',
    'stats',
    'format_analysis_summary',
    'parse_log_line'
]