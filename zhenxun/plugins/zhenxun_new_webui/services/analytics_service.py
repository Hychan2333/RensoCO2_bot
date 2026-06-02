"""数据分析服务"""

import asyncio
from datetime import datetime, timedelta
from typing import Literal

from zhenxun.models.chat_history import ChatHistory
from zhenxun.models.sign_user import SignUser
from zhenxun.models.statistics import Statistics
from zhenxun.models.user_console import UserConsole
from zhenxun.services.log import logger

from ..models.analytics import (
    DetailedStatisticsTimeRange,
    FavorabilityRank,
    FriendStatisticsTimeRange,
    GoldRank,
    GroupStatisticsTimeRange,
    TrendData,
    TrendPoint,
)
from .common import (
    get_group_name_map,
    get_user_name_map,
    grouped_count_map,
    merge_keys,
    qq_avatar_url,
    safe_count,
)

Granularity = Literal["hour", "day", "week", "month"]


class AnalyticsService:
    """数据分析服务"""

    @staticmethod
    def generate_time_ranges(
        start_time: datetime,
        end_time: datetime,
        granularity: Granularity,
    ) -> list[tuple[datetime, datetime]]:
        """生成时间范围列表

        参数:
            start_time: 起始时间
            end_time: 结束时间
            granularity: 时间粒度

        返回:
            list[tuple[datetime, datetime]]: 时间范围列表 [(start, end), ...]
        """
        ranges = []
        current = start_time

        while current < end_time:
            if granularity == "hour":
                next_time = current + timedelta(hours=1)
            elif granularity == "day":
                next_time = current + timedelta(days=1)
            elif granularity == "week":
                # 按周分组（周一为一周开始）
                days_until_monday = (7 - current.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                next_time = current + timedelta(days=days_until_monday)
            elif granularity == "month":
                # 按月分组
                if current.month == 12:
                    next_time = current.replace(year=current.year + 1, month=1, day=1)
                else:
                    next_time = current.replace(month=current.month + 1, day=1)
            else:
                next_time = current + timedelta(days=1)

            # 确保不超过结束时间
            actual_end = min(next_time, end_time)
            ranges.append((current, actual_end))
            current = next_time

        return ranges

    @staticmethod
    async def get_trend_data(
        start_time: datetime,
        end_time: datetime,
        granularity: Granularity = "day",
        bot_id: str | None = None,
    ) -> TrendData:
        """获取趋势数据

        参数:
            start_time: 起始时间
            end_time: 结束时间
            granularity: 时间粒度 (hour/day/week/month)
            bot_id: Bot ID，可选

        返回:
            TrendData: 趋势数据
        """
        time_ranges = AnalyticsService.generate_time_ranges(
            start_time, end_time, granularity
        )

        data_points = []
        total_messages = 0
        total_calls = 0

        for range_start, range_end in time_ranges:
            # 查询消息数量
            msg_query = ChatHistory.filter(
                create_time__gte=range_start,
                create_time__lt=range_end,
            )
            if bot_id:
                msg_query = msg_query.filter(bot_id=bot_id)
            call_query = Statistics.filter(
                create_time__gte=range_start,
                create_time__lt=range_end,
            )
            if bot_id:
                call_query = call_query.filter(bot_id=bot_id)

            msg_count, call_count = await asyncio.gather(
                safe_count(msg_query),
                safe_count(call_query),
            )

            data_points.append(
                TrendPoint(
                    timestamp=range_start,
                    message_count=msg_count,
                    plugin_call_count=call_count,
                )
            )

            total_messages += msg_count
            total_calls += call_count

        return TrendData(
            data_points=data_points,
            total_message_count=total_messages,
            total_plugin_call_count=total_calls,
            granularity=granularity,
            start_time=start_time,
            end_time=end_time,
        )

    @staticmethod
    async def get_detailed_statistics(
        start_time: datetime,
        end_time: datetime,
        bot_id: str | None = None,
    ) -> DetailedStatisticsTimeRange:
        """获取详细统计数据（带时间范围）

        参数:
            start_time: 起始时间
            end_time: 结束时间
            bot_id: Bot ID，可选

        返回:
            DetailedStatisticsTimeRange: 详细统计数据
        """
        # 群组统计
        group_stats = []
        try:
            # 按群组 ID 分组统计消息数量
            group_msg_query = ChatHistory.filter(
                group_id__not_isnull=True,
                create_time__gte=start_time,
                create_time__lt=end_time,
            )
            if bot_id:
                group_msg_query = group_msg_query.filter(bot_id=bot_id)

            group_call_query = Statistics.filter(
                group_id__not_isnull=True,
                create_time__gte=start_time,
                create_time__lt=end_time,
            )
            if bot_id:
                group_call_query = group_call_query.filter(bot_id=bot_id)

            group_msg_map, group_call_map = await asyncio.gather(
                grouped_count_map(group_msg_query, "group_id"),
                grouped_count_map(group_call_query, "group_id"),
            )
            all_group_ids = merge_keys(group_msg_map, group_call_map)
            group_name_map = await get_group_name_map(all_group_ids)

            for group_id in all_group_ids:
                group_stats.append(
                    GroupStatisticsTimeRange(
                        group_id=group_id,
                        group_name=group_name_map.get(str(group_id), f"群 {group_id}"),
                        message_count=group_msg_map.get(group_id, 0),
                        plugin_call_count=group_call_map.get(group_id, 0),
                    )
                )

            # 按消息数量降序排序
            group_stats.sort(key=lambda x: x.message_count, reverse=True)
        except Exception as e:
            logger.error(f"获取群组统计失败：{e}", "AnalyticsService")

        # 好友统计
        friend_stats = []
        try:
            # 按用户 ID 分组统计私聊消息数量
            friend_msg_query = ChatHistory.filter(
                group_id__isnull=True,
                create_time__gte=start_time,
                create_time__lt=end_time,
            )
            if bot_id:
                friend_msg_query = friend_msg_query.filter(bot_id=bot_id)

            friend_call_query = Statistics.filter(
                group_id__isnull=True,
                create_time__gte=start_time,
                create_time__lt=end_time,
            )
            if bot_id:
                friend_call_query = friend_call_query.filter(bot_id=bot_id)

            friend_msg_map, friend_call_map = await asyncio.gather(
                grouped_count_map(friend_msg_query, "user_id"),
                grouped_count_map(friend_call_query, "user_id"),
            )
            all_user_ids = merge_keys(friend_msg_map, friend_call_map)
            user_name_map = await get_user_name_map(all_user_ids)

            for user_id in all_user_ids:
                friend_stats.append(
                    FriendStatisticsTimeRange(
                        user_id=user_id,
                        user_name=user_name_map.get(str(user_id), f"用户 {user_id}"),
                        message_count=friend_msg_map.get(user_id, 0),
                        plugin_call_count=friend_call_map.get(user_id, 0),
                    )
                )

            # 按消息数量降序排序
            friend_stats.sort(key=lambda x: x.message_count, reverse=True)
        except Exception as e:
            logger.error(f"获取好友统计失败：{e}", "AnalyticsService")

        return DetailedStatisticsTimeRange(
            groups=group_stats,
            friends=friend_stats,
            start_time=start_time,
            end_time=end_time,
        )

    @staticmethod
    async def get_favorability_top10(
        bot_id: str | None = None,
    ) -> list[FavorabilityRank]:
        """获取好感度 top10 用户

        参数:
            bot_id: Bot ID，可选

        返回:
            list[FavorabilityRank]: 好感度排名列表
        """
        query = SignUser.all().filter(impression__gt=0)
        if bot_id:
            # 如果需要按 bot_id 过滤，可以通过 user_console 关联
            # 这里暂时不过滤，因为好感度是全局的
            pass

        # 按好感度降序排序，取前 10 名
        sign_users = (
            await query.order_by("-impression")
            .limit(10)
            .prefetch_related("user_console")
        )

        result = []
        for sign_user in sign_users:
            user_console = sign_user.user_console
            result.append(
                FavorabilityRank(
                    user_id=user_console.user_id if user_console else sign_user.user_id,
                    user_name=user_console.user_id
                    if user_console
                    else sign_user.user_id,
                    favorability=float(sign_user.impression),
                    ava_url=qq_avatar_url(sign_user.user_id),
                )
            )

        return result

    @staticmethod
    async def get_gold_top10(
        bot_id: str | None = None,
    ) -> list[GoldRank]:
        """获取金币 top10 用户

        参数:
            bot_id: Bot ID，可选

        返回:
            list[GoldRank]: 金币排名列表
        """
        query = UserConsole.all().filter(gold__gt=0)

        # 按金币降序排序，取前 10 名
        users = await query.order_by("-gold").limit(10)

        result = []
        for user in users:
            result.append(
                GoldRank(
                    user_id=user.user_id,
                    user_name=user.user_id,
                    gold=user.gold,
                    ava_url=qq_avatar_url(user.user_id),
                )
            )

        return result
