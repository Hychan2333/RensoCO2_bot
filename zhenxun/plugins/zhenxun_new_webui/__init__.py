"""WebUI Next - 重构后的 WebUI 后端"""

import secrets

from fastapi import APIRouter
import nonebot
from nonebot.plugin import PluginMetadata

from zhenxun.configs.config import Config as gConfig
from zhenxun.configs.utils import PluginExtraData, RegisterConfig
from zhenxun.services.log import logger
from zhenxun.utils.enum import PluginType
from zhenxun.utils.manager.priority_manager import PriorityLifecycle

# 导入配置以注册 CORS 中间件
from . import config as _config  # noqa: F401
from .lifecycle import setup_webui
from .routers import (
    analytics_router,
    auth_router,
    config_router,
    dashboard_router,
    database_router,
    file_router,
    main_router,
    manage_router,
    plugin_router,
    store_router,
    system_router,
)
from .routers.websocket import ws_chat_router, ws_log_router, ws_status_router

__plugin_meta__ = PluginMetadata(
    name="WebUi Next",
    description="重构后的 WebUI API",
    usage='"""\n    """.strip(),',
    extra=PluginExtraData(
        author="NegiChan",
        version="0.2",
        plugin_type=PluginType.HIDDEN,
        configs=[
            RegisterConfig(
                module="web-ui",
                key="username",
                value="admin",
                help="前端管理用户名",
                type=str,
                default_value="admin",
            ),
            RegisterConfig(
                module="web-ui",
                key="password",
                value=None,
                help="前端管理密码",
                type=str,
                default_value=None,
            ),
            RegisterConfig(
                module="web-ui",
                key="secret",
                value=secrets.token_urlsafe(32),
                help="JWT 密钥",
                type=str,
                default_value=None,
            ),
        ],
    ).to_dict(),
)

driver = nonebot.get_driver()

gConfig.set_name("web-ui", "web-ui")

# HTTP API 路由 - 统一使用 /zhenxun/api/v1 前缀
BaseApiRouter = APIRouter(prefix="/zhenxun/api/v1")

for router in (
    auth_router,
    analytics_router,
    dashboard_router,
    main_router,
    plugin_router,
    system_router,
    file_router,
    config_router,
    database_router,
    store_router,
    manage_router,
):
    BaseApiRouter.include_router(router)

# WebSocket API 路由 - 统一使用 /zhenxun/ws/v1 前缀
WsApiRouter = APIRouter(prefix="/zhenxun/ws/v1")

for router in (ws_log_router, ws_status_router, ws_chat_router):
    WsApiRouter.include_router(router)


@PriorityLifecycle.on_startup(priority=0)
async def _():
    try:
        setup_webui(nonebot.get_app(), BaseApiRouter, WsApiRouter)
        logger.info("<g>WebUI Next API 启动成功</g>", "WebUiNext")

    except Exception as e:
        logger.error("<g>WebUI Next API 启动失败</g>", "WebUiNext", e=e)
