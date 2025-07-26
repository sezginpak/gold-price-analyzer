"""
Web utility modulleri
"""

from .cache import CacheManager
from .stats import StatsManager
from .formatters import format_analysis_summary, parse_log_line

cache = CacheManager()
stats = StatsManager()

__all__ = [
    'cache',
    'stats',
    'format_analysis_summary',
    'parse_log_line'
]