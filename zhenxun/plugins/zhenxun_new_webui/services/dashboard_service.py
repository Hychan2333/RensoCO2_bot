"""仪表盘服务"""

import asyncio
from datetime import datetime, timedelta

from zhenxun.models.chat_history import ChatHistory
from zhenxun.models.group_console import GroupConsole
from zhenxun.models.statistics import Statistics
from zhenxun.models.user_console import UserConsole
from zhenxun.services.log import logger

from ..models.dashboard import (
    DashboardOverview,
    DashboardResult,
    DashboardStats,
    DetailedStatistics,
    FriendStatistics,
    GroupStatistics,
    QuickAction,
    StatItem,
)
from .common import (
    get_group_name_map,
    get_today_start,
    get_user_name_map,
    grouped_count_map,
    merge_keys,
    safe_count,
)
from .system_service import get_system_health

# 模块级缓存，避免重复定义
QUICK_ACTIONS = [
    QuickAction(
        name="重启 Bot",
        description="重启机器人服务",
        icon="refresh",
        action_type="restart",
    ),
    QuickAction(
        name="清理缓存",
        description="清理系统缓存",
        icon="clean",
        action_type="clear_cache",
    ),
    QuickAction(
        name="查看日志",
        description="查看系统日志",
        icon="file-text",
        action_type="view_logs",
    ),
    QuickAction(
        name="备份数据", description="备份数据库", icon="database", action_type="backup"
    ),
]


def _calc_trend(current: int, previous: int) -> tuple[str, float | None]:
    """计算趋势"""
    if previous == 0:
        return ("stable", None) if current == 0 else ("up", 100.0)
    change = ((current - previous) / previous) * 100
    if change > 5:
        return ("up", change)
    if change < -5:
        return ("down", change)
    return ("stable", change)


class DashboardService:
    """仪表盘服务"""

    @staticmethod
    async def get_dashboard() -> DashboardResult:
        """获取仪表盘数据"""
        overview, stats, health = await asyncio.gather(
            DashboardService._get_overview(),
            DashboardService._get_stats(),
            get_system_health(),
        )

        return DashboardResult(
            overview=overview,
            stats=stats,
            quick_actions=QUICK_ACTIONS,
            system_health=health.status,
        )

    @staticmethod
    async def _get_overview() -> DashboardOverview:
        """获取概览数据"""
        import nonebot

        bots = nonebot.get_bots()
        bot_status = "online" if bots else "offline"

        # 运行时长
        uptime = 0
        uptime_formatted = "0 秒"
        try:
            from zhenxun.models.bot_console import BotConsole
            from zhenxun.utils.formatters import format_uptime

            bot_console = await BotConsole.first()
            if bot_console and bot_console.create_time:
                uptime = int((datetime.now() - bot_console.create_time).total_seconds())
                uptime_formatted = format_uptime(uptime)
        except Exception:
            pass

        friend_count = 0
        group_count = await safe_count(GroupConsole.all())

        message_count_today = await safe_count(
            ChatHistory.filter(create_time__gte=get_today_start())
        )

        # 插件数量
        plugin_count = 0
        enabled_plugin_count = 0
        try:
            from zhenxun.models.plugin_info import PluginInfo

            plugin_count, enabled_plugin_count = await asyncio.gather(
                safe_count(PluginInfo.filter(load_status=True)),
                safe_count(PluginInfo.filter(load_status=True, status=True)),
            )
        except Exception:
            pass

        return DashboardOverview(
            bot_status=bot_status,
            uptime=uptime,
            uptime_formatted=uptime_formatted,
            group_count=group_count,
            friend_count=friend_count,
            message_count_today=message_count_today,
            plugin_count=plugin_count,
            enabled_plugin_count=enabled_plugin_count,
        )

    @staticmethod
    async def _get_stats() -> DashboardStats:
        """获取统计数据"""
        now = datetime.now()
        today_start = get_today_start(now)
        yesterday_start = get_today_start(now - timedelta(days=1))

        from zhenxun.models.bot_connect_log import BotConnectLog

        (
            message_total,
            message_yesterday,
            user_count,
            group_count,
            error_count,
        ) = await asyncio.gather(
            safe_count(ChatHistory.filter(create_time__gte=today_start)),
            safe_count(
                ChatHistory.filter(
                    create_time__gte=yesterday_start,
                    create_time__lt=today_start,
                )
            ),
            safe_count(UserConsole.all()),
            safe_count(GroupConsole.all()),
            safe_count(BotConnectLog.filter(create_time__gte=now - timedelta(days=7))),
        )
        message_trend, message_change = _calc_trend(message_total, message_yesterday)

        return DashboardStats(
            message_stats=StatItem(
                label="消息数量",
                value=message_total,
                trend=message_trend,
                change=message_change,
            ),
            user_stats=StatItem(label="用户数量", value=user_count, trend="stable"),
            group_stats=StatItem(label="群组数量", value=group_count, trend="stable"),
            error_stats=StatItem(label="错误数量", value=error_count, trend="stable"),
        )

    @staticmethod
    async def get_detailed_statistics() -> DetailedStatistics:
        """获取详细统计数据（群组/好友消息和调用情况）"""
        now = datetime.now()
        today_start = get_today_start(now)

        group_stats, friend_stats = await asyncio.gather(
            DashboardService._get_group_statistics(today_start),
            DashboardService._get_friend_statistics(today_start),
        )

        return DetailedStatistics(groups=group_stats, friends=friend_stats)

    @staticmethod
    async def _get_group_statistics(today_start: datetime) -> list[GroupStatistics]:
        """获取群组统计数据"""
        group_stats = []
        try:
            group_msg_query = ChatHistory.filter(
                group_id__not_isnull=True, create_time__gte=today_start
            )
            group_call_query = Statistics.filter(
                group_id__not_isnull=True, create_time__gte=today_start
            )
            group_msg_map, group_call_map = await asyncio.gather(
                grouped_count_map(group_msg_query, "group_id"),
                grouped_count_map(group_call_query, "group_id"),
            )
            all_group_ids = merge_keys(group_msg_map, group_call_map)
            group_name_map = await get_group_name_map(all_group_ids)

            for group_id in all_group_ids:
                group_stats.append(
                    GroupStatistics(
                        group_id=group_id,
                        group_name=group_name_map.get(str(group_id), f"群 {group_id}"),
                        message_count=group_msg_map.get(group_id, 0),
                        plugin_call_count=group_call_map.get(group_id, 0),
                    )
                )

            group_stats.sort(key=lambda x: x.message_count, reverse=True)
        except Exception as e:
            logger.error(f"获取群组统计失败：{e}", "DashboardService")

        return group_stats

    @staticmethod
    async def _get_friend_statistics(today_start: datetime) -> list[FriendStatistics]:
        """获取好友统计数据"""
        friend_stats = []
        try:
            friend_msg_query = ChatHistory.filter(
                group_id__isnull=True, create_time__gte=today_start
            )
            friend_call_query = Statistics.filter(
                group_id__isnull=True, create_time__gte=today_start
            )
            friend_msg_map, friend_call_map = await asyncio.gather(
                grouped_count_map(friend_msg_query, "user_id"),
                grouped_count_map(friend_call_query, "user_id"),
            )
            all_user_ids = merge_keys(friend_msg_map, friend_call_map)
            user_name_map = await get_user_name_map(all_user_ids)

            for user_id in all_user_ids:
                friend_stats.append(
                    FriendStatistics(
                        user_id=user_id,
                        user_name=user_name_map.get(str(user_id), f"用户 {user_id}"),
                        message_count=friend_msg_map.get(user_id, 0),
                        plugin_call_count=friend_call_map.get(user_id, 0),
                    )
                )

            friend_stats.sort(key=lambda x: x.message_count, reverse=True)
        except Exception as e:
            logger.error(f"获取好友统计失败：{e}", "DashboardService")

        return friend_stats
