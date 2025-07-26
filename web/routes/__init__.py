"""
Web route modulleri
"""

from .dashboard import router as dashboard_router
from .api import router as api_router
from .analysis import router as analysis_router
from .simulation import router as simulation_router
from .static import router as static_router

__all__ = [
    'dashboard_router',
    'api_router',
    'analysis_router',
    'simulation_router',
    'static_router'
]