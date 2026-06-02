"""插件路由"""

from ..dependencies import AuthenticatedUser
from ..models.plugin import (
    PluginConfigResult,
    PluginListRequest,
    PluginListResult,
    PluginToggleRequest,
)
from ..responses import APIResponse, success_response
from ..routing import WebUIRouter
from ..services.plugin_service import PluginService

router = WebUIRouter(prefix="/plugin", tags=["插件管理"])


@router.post(
    "/list",
    response_model=APIResponse[PluginListResult],
    summary="获取插件列表",
)
async def get_plugin_list(
    user: AuthenticatedUser, request: PluginListRequest
) -> APIResponse[PluginListResult]:
    """获取插件列表

    支持搜索、状态过滤、类型过滤和分页。
    """
    result = await PluginService.get_plugin_list(request)
    return success_response(data=result)


@router.post(
    "/toggle",
    response_model=APIResponse[bool],
    summary="切换插件状态",
)
async def toggle_plugin(
    user: AuthenticatedUser, request: PluginToggleRequest
) -> APIResponse[bool]:
    """切换插件启用/禁用状态"""
    result = await PluginService.toggle_plugin(request)
    return success_response(data=result, message="状态已更新")


@router.get(
    "/config/{module}",
    response_model=APIResponse[PluginConfigResult],
    summary="获取插件配置",
)
async def get_plugin_config(
    user: AuthenticatedUser, module: str
) -> APIResponse[PluginConfigResult]:
    """获取指定插件的配置"""
    result = await PluginService.get_plugin_config(module)
    return success_response(data=result)


@router.get(
    "/detail/{module}",
    response_model=APIResponse[dict],
    summary="获取插件详情",
)
async def get_plugin_detail(user: AuthenticatedUser, module: str) -> APIResponse[dict]:
    """获取指定插件的详细信息"""
    result = await PluginService.get_plugin_detail(module)
    return success_response(data=result)
