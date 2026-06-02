"""主页路由"""

from ..dependencies import AuthenticatedUser
from ..exceptions import APIException
from ..models.system import BotInfo, BotStatus, BotStatusListData
from ..responses import APIResponse, success_response
from ..routing import WebUIRouter
from ..services.main_service import MainService

router = WebUIRouter(prefix="/main", tags=["主页"])


@router.get(
    "/bot-status",
    response_model=APIResponse[BotStatus],
    summary="获取 Bot 状态",
)
async def get_bot_status(
    user: AuthenticatedUser, bot_id: str | None = None
) -> APIResponse[BotStatus]:
    """获取 Bot 运行状态

    Returns:
        APIResponse[BotStatus]: Bot 状态
    """
    try:
        result = await MainService.get_bot_status(bot_id)
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取 Bot 状态失败：{e!s}", code=500)


@router.get(
    "/bot-status/list",
    response_model=APIResponse[BotStatusListData],
    summary="获取 Bot 状态列表",
)
async def get_bot_status_list(
    user: AuthenticatedUser, bot_id: str | None = None
) -> APIResponse[BotStatusListData]:
    """获取 Bot 状态列表"""
    try:
        result = await MainService.get_bot_status_list(bot_id)
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取 Bot 状态列表失败：{e!s}", code=500)


@router.get(
    "/bot-list",
    response_model=APIResponse[list[BotInfo]],
    summary="获取 Bot 列表",
)
async def get_bot_list(user: AuthenticatedUser) -> APIResponse[list[BotInfo]]:
    """获取 Bot 状态列表"""
    try:
        result = await MainService.get_bot_list()
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取 Bot 状态列表失败：{e!s}", code=500)


@router.get(
    "/chat-statistics",
    response_model=APIResponse[dict],
    summary="获取聊天统计",
)
async def get_chat_statistics(
    user: AuthenticatedUser, bot_id: str | None = None
) -> APIResponse[dict]:
    """获取聊天统计数据

    Args:
        bot_id: Bot ID，可选

    Returns:
        APIResponse[dict]: 统计数据
    """
    try:
        result = await MainService.get_chat_statistics(bot_id)
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取聊天统计失败：{e!s}", code=500)


@router.get(
    "/plugin-statistics",
    response_model=APIResponse[dict],
    summary="获取插件调用统计",
)
async def get_plugin_statistics(
    user: AuthenticatedUser, bot_id: str | None = None
) -> APIResponse[dict]:
    """获取插件调用统计数据

    Args:
        bot_id: Bot ID，可选

    Returns:
        APIResponse[dict]: 统计数据
    """
    try:
        result = await MainService.get_plugin_statistics(bot_id)
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取插件统计失败：{e!s}", code=500)


@router.get(
    "/active-groups",
    response_model=APIResponse[list[dict]],
    summary="获取活跃群组",
)
async def get_active_groups(
    user: AuthenticatedUser,
    start_time: str | None = None,
    end_time: str | None = None,
    date_type: str = "week",
    bot_id: str | None = None,
) -> APIResponse[list[dict]]:
    """获取活跃群组列表

    Args:
        start_time: 起始时间 (ISO 8601 格式)，可选
        end_time: 结束时间 (ISO 8601 格式)，可选
        date_type: 日期类型 (day/week/month/year)，当未提供 start_time/end_time 时使用
        bot_id: Bot ID，可选

    Returns:
        APIResponse[list[dict]]: 活跃群组列表
    """
    try:
        result = await MainService.get_active_groups(
            start_time, end_time, date_type, bot_id
        )
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取活跃群组失败：{e!s}", code=500)


@router.get(
    "/hot-plugins",
    response_model=APIResponse[list[dict]],
    summary="获取热门插件",
)
async def get_hot_plugins(
    user: AuthenticatedUser,
    start_time: str | None = None,
    end_time: str | None = None,
    date_type: str = "week",
    bot_id: str | None = None,
) -> APIResponse[list[dict]]:
    """获取热门插件列表

    Args:
        start_time: 起始时间 (ISO 8601 格式)，可选
        end_time: 结束时间 (ISO 8601 格式)，可选
        date_type: 日期类型 (day/week/month/year)，当未提供 start_time/end_time 时使用
        bot_id: Bot ID，可选

    Returns:
        APIResponse[list[dict]]: 热门插件列表
    """
    try:
        result = await MainService.get_hot_plugins(
            start_time, end_time, date_type, bot_id
        )
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取热门插件失败：{e!s}", code=500)
