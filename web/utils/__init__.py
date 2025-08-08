"""
Web utility modulleri
"""

from .cache import CacheManager
from .stats import StatsManager
from .formatters import format_analysis_summary, parse_log_line

# Ultra optimized cache with intelligent TTL, compression and 3000 max entries
cache = CacheManager(default_ttl=180, max_entries=3000, enable_compression=True)
stats = StatsManager()

__all__ = [
    'cache',
    'stats',
    'format_analysis_summary',
    'parse_log_line'
]