"""路由层导出"""

from .analytics import router as analytics_router
from .auth import router as auth_router
from .config import router as config_router
from .dashboard import router as dashboard_router
from .database import router as database_router
from .file import router as file_router
from .main import router as main_router
from .manage import router as manage_router
from .plugin import router as plugin_router
from .store import router as store_router
from .system import router as system_router
from .websocket import ws_chat_router, ws_log_router, ws_status_router

__all__ = [
    "analytics_router",
    "auth_router",
    "config_router",
    "dashboard_router",
    "database_router",
    "file_router",
    "main_router",
    "manage_router",
    "plugin_router",
    "store_router",
    "system_router",
    "ws_chat_router",
    "ws_log_router",
    "ws_status_router",
]
