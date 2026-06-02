"""后端服务公共工具。"""

import asyncio
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

import nonebot
from nonebot.adapters import Bot
from tortoise.functions import Count

from zhenxun.models.friend_user import FriendUser
from zhenxun.models.group_console import GroupConsole


def get_default_bot() -> Bot | None:
    """获取当前第一个可用 Bot。"""
    bots = nonebot.get_bots()
    return next(iter(bots.values()), None)


def get_bot(bot_id: str | None = None) -> Bot | None:
    """按 bot_id 获取 Bot，未指定时返回默认 Bot。"""
    if bot_id:
        return nonebot.get_bot(bot_id)
    return get_default_bot()


def qq_avatar_url(user_id: str | int | None, size: int = 640) -> str:
    """生成 QQ 用户头像 URL。"""
    return f"http://q1.qlogo.cn/g?b=qq&nk={user_id or ''}&s={size}"


def qq_group_avatar_url(group_id: str | int | None, size: int = 640) -> str:
    """生成 QQ 群头像 URL。"""
    value = group_id or ""
    return f"http://p.qlogo.cn/gh/{value}/{value}/{size}/"


def get_today_start(now: datetime | None = None) -> datetime:
    """获取当天开始时间。"""
    value = now or datetime.now()
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


async def safe_count(query: Any, default: int = 0) -> int:
    """安全执行 count 查询。"""
    try:
        return await query.count()
    except Exception:
        return default


async def count_time_buckets(query: Any, now: datetime | None = None) -> dict[str, int]:
    """并发统计 all/day/week/month/year。"""
    current = now or datetime.now()
    today_start = get_today_start(current)
    all_count, day, week, month, year = await asyncio.gather(
        safe_count(query),
        safe_count(query.filter(create_time__gte=today_start)),
        safe_count(query.filter(create_time__gte=today_start - timedelta(days=7))),
        safe_count(query.filter(create_time__gte=today_start - timedelta(days=30))),
        safe_count(query.filter(create_time__gte=today_start - timedelta(days=365))),
    )
    return {
        "all": all_count,
        "day": day,
        "week": week,
        "month": month,
        "year": year,
    }


async def grouped_count_map(query: Any, field: str) -> dict[Any, int]:
    """按字段分组统计 count。"""
    rows = (
        await query.annotate(count=Count("id")).group_by(field).values(field, "count")
    )
    return {row[field]: row["count"] for row in rows}


def merge_keys(*maps: dict[Any, Any]) -> set[Any]:
    """合并多个映射的 key。"""
    keys: set[Any] = set()
    for item in maps:
        keys.update(item.keys())
    return keys


async def get_group_name_map(group_ids: Iterable[Any]) -> dict[str, str]:
    """批量获取群名称映射。"""
    ids = [str(group_id) for group_id in set(group_ids) if group_id is not None]
    if not ids:
        return {}
    groups = await GroupConsole.filter(group_id__in=ids).all()
    return {str(group.group_id): group.group_name for group in groups}


async def get_user_name_map(user_ids: Iterable[Any]) -> dict[str, str]:
    """批量获取用户名称映射。"""
    ids = [str(user_id) for user_id in set(user_ids) if user_id is not None]
    if not ids:
        return {}
    users = await FriendUser.filter(user_id__in=ids).all()
    return {str(user.user_id): user.user_name for user in users if user.user_name}


def apply_time_range_filter(
    query: Any,
    start_time: str | None = None,
    end_time: str | None = None,
    date_type: str = "week",
) -> Any:
    """为 Tortoise 查询追加时间范围过滤。"""
    if start_time and end_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            return query.filter(create_time__gte=start_dt, create_time__lte=end_dt)
        except ValueError:
            pass

    now = datetime.now()
    today_start = get_today_start(now)
    if date_type == "day":
        start = today_start
    elif date_type == "week":
        start = today_start - timedelta(days=7)
    elif date_type == "month":
        start = today_start - timedelta(days=30)
    elif date_type == "year":
        start = today_start - timedelta(days=365)
    else:
        start = today_start - timedelta(days=7)
    return query.filter(create_time__gte=start)
