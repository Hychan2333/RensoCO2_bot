"""数据分析相关模型"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Granularity(str, Enum):
    """时间粒度枚举"""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TrendPoint(BaseModel):
    """趋势数据点"""

    timestamp: datetime = Field(..., description="时间点")
    message_count: int = Field(..., description="消息数量")
    plugin_call_count: int = Field(..., description="插件调用次数")


class TrendData(BaseModel):
    """趋势数据响应"""

    data_points: list[TrendPoint] = Field(
        default_factory=list, description="数据点列表"
    )
    total_message_count: int = Field(..., description="总消息数")
    total_plugin_call_count: int = Field(..., description="总调用次数")
    granularity: str = Field(..., description="时间粒度")
    start_time: datetime = Field(..., description="起始时间")
    end_time: datetime = Field(..., description="结束时间")


class GroupStatisticsTimeRange(BaseModel):
    """带时间范围的群组统计"""

    group_id: str = Field(..., description="群组 ID")
    group_name: str = Field(..., description="群组名称")
    message_count: int = Field(..., description="消息数量")
    plugin_call_count: int = Field(..., description="插件调用次数")


class FriendStatisticsTimeRange(BaseModel):
    """带时间范围的好友统计"""

    user_id: str = Field(..., description="用户 ID")
    user_name: str = Field(..., description="用户名称")
    message_count: int = Field(..., description="消息数量")
    plugin_call_count: int = Field(..., description="插件调用次数")


class DetailedStatisticsTimeRange(BaseModel):
    """带时间范围的详细统计数据"""

    groups: list[GroupStatisticsTimeRange] = Field(
        default_factory=list, description="群组统计列表"
    )
    friends: list[FriendStatisticsTimeRange] = Field(
        default_factory=list, description="好友统计列表"
    )
    start_time: datetime = Field(..., description="查询起始时间")
    end_time: datetime = Field(..., description="查询结束时间")


class FavorabilityRank(BaseModel):
    """好感度排名"""

    user_id: str = Field(..., description="用户 ID")
    user_name: str = Field(..., description="用户名称")
    favorability: float = Field(..., description="好感度值")
    ava_url: str = Field(..., description="头像 URL")


class GoldRank(BaseModel):
    """金币排名"""

    user_id: str = Field(..., description="用户 ID")
    user_name: str = Field(..., description="用户名称")
    gold: int = Field(..., description="金币数量")
    ava_url: str = Field(..., description="头像 URL")
