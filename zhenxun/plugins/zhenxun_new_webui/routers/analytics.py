"""数据分析路由"""

from datetime import datetime

from fastapi import Query

from ..dependencies import AuthenticatedUser
from ..exceptions import APIException
from ..models.analytics import (
    DetailedStatisticsTimeRange,
    FavorabilityRank,
    GoldRank,
    TrendData,
)
from ..responses import APIResponse, success_response
from ..routing import WebUIRouter
from ..services.analytics_service import AnalyticsService

router = WebUIRouter(prefix="/analytics", tags=["数据分析"])


@router.get(
    "/trend",
    response_model=APIResponse[TrendData],
    summary="获取趋势数据",
)
async def get_trend_data(
    user: AuthenticatedUser,
    start_time: datetime = Query(..., description="起始时间 (ISO 格式)"),
    end_time: datetime = Query(..., description="结束时间 (ISO 格式)"),
    granularity: str = Query("day", description="时间粒度：hour/day/week/month"),
    bot_id: str | None = Query(None, description="Bot ID"),
) -> APIResponse[TrendData]:
    """获取趋势数据

    按指定时间粒度返回消息数量和插件调用次数的趋势数据。

    Args:
        start_time: 起始时间 (ISO 格式)
        end_time: 结束时间 (ISO 格式)
        granularity: 时间粒度 (hour/day/week/month)
        bot_id: Bot ID，可选

    Returns:
        APIResponse[TrendData]: 趋势数据
    """
    try:
        # 验证时间范围
        if start_time >= end_time:
            raise APIException("起始时间必须早于结束时间", code=400)

        # 验证时间粒度
        valid_granularities = ["hour", "day", "week", "month"]
        if granularity not in valid_granularities:
            raise APIException(
                f"无效的时间粒度，有效值：{', '.join(valid_granularities)}", code=400
            )

        result = await AnalyticsService.get_trend_data(
            start_time=start_time,
            end_time=end_time,
            granularity=granularity,  # type: ignore
            bot_id=bot_id,
        )
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取趋势数据失败：{e!s}", code=500)


@router.get(
    "/statistics",
    response_model=APIResponse[DetailedStatisticsTimeRange],
    summary="获取详细统计（带时间范围）",
)
async def get_statistics(
    user: AuthenticatedUser,
    start_time: datetime = Query(..., description="起始时间 (ISO 格式)"),
    end_time: datetime = Query(..., description="结束时间 (ISO 格式)"),
    bot_id: str | None = Query(None, description="Bot ID"),
) -> APIResponse[DetailedStatisticsTimeRange]:
    """获取详细统计数据

    返回指定时间范围内的群组/好友消息和插件调用统计。

    Args:
        start_time: 起始时间 (ISO 格式)
        end_time: 结束时间 (ISO 格式)
        bot_id: Bot ID，可选

    Returns:
        APIResponse[DetailedStatisticsTimeRange]: 详细统计数据
    """
    try:
        # 验证时间范围
        if start_time >= end_time:
            raise APIException("起始时间必须早于结束时间", code=400)

        result = await AnalyticsService.get_detailed_statistics(
            start_time=start_time,
            end_time=end_time,
            bot_id=bot_id,
        )
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取详细统计数据失败：{e!s}", code=500)


@router.get(
    "/favorability-top10",
    response_model=APIResponse[list[FavorabilityRank]],
    summary="获取好感度 top10",
)
async def get_favorability_top10(
    user: AuthenticatedUser,
    bot_id: str | None = Query(None, description="Bot ID"),
) -> APIResponse[list[FavorabilityRank]]:
    """获取好感度 top10 用户

    Args:
        bot_id: Bot ID，可选

    Returns:
        APIResponse[list[FavorabilityRank]]: 好感度排名列表
    """
    try:
        result = await AnalyticsService.get_favorability_top10(bot_id)
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取好感度排名失败：{e!s}", code=500)


@router.get(
    "/gold-top10",
    response_model=APIResponse[list[GoldRank]],
    summary="获取金币 top10",
)
async def get_gold_top10(
    user: AuthenticatedUser,
    bot_id: str | None = Query(None, description="Bot ID"),
) -> APIResponse[list[GoldRank]]:
    """获取金币 top10 用户

    Args:
        bot_id: Bot ID，可选

    Returns:
        APIResponse[list[GoldRank]]: 金币排名列表
    """
    try:
        result = await AnalyticsService.get_gold_top10(bot_id)
        return success_response(data=result)
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取金币排名失败：{e!s}", code=500)
