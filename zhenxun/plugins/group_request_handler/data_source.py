"""数据处理模块"""

import re
from typing import Literal

from nonebot.adapters.onebot.v11 import Bot

from zhenxun.configs.config import Config
from zhenxun.services.log import logger

from .data_manager import GroupRequestDataManager


class GroupRequestHandler:
    """加群申请处理器"""

    def __init__(self, data_manager: GroupRequestDataManager):
        self.data_manager = data_manager

    async def get_qq_level(self, bot: Bot, user_id: int) -> int:
        """
        获取用户的QQ等级

        Args:
            bot: Bot实例
            user_id: 用户QQ号

        Returns:
            QQ等级
        """
        try:
            user_info = await bot.get_stranger_info(user_id=user_id)
            # OneBot v11 返回的用户信息中包含 level 字段
            return user_info.get("level", 0)
        except Exception as e:
            logger.error(
                f"获取用户 {user_id} 的QQ等级失败: {e}",
                "加群申请处理",
                target=user_id,
            )
            return 0

    async def check_qq_level(self, group_id: str, level: int) -> bool:
        """
        检查QQ等级是否满足要求（支持群专属配置）

        Args:
            group_id: 群号
            level: QQ等级

        Returns:
            是否满足要求
        """
        # 获取群专属的最低等级要求
        min_level = await self.data_manager.get_min_level(group_id)

        # 如果没有设置群专属配置，使用全局配置
        if min_level is None:
            min_level = Config.get_config("group_request_handler", "MIN_QQ_LEVEL")

        return level >= min_level

    async def check_blacklist(self, group_id: str, reason: str) -> tuple[bool, str | None]:
        """
        检查加群理由是否匹配黑名单

        Args:
            group_id: 群号
            reason: 加群理由

        Returns:
            (是否匹配黑名单, 拒绝理由)
        """
        blacklist = await self.data_manager.get_blacklist(group_id)

        for item in blacklist:
            pattern = item.get("pattern", "")
            reject_reason = item.get("reason", "")

            try:
                if re.match(pattern, reason, re.DOTALL):
                    logger.info(
                        f"加群理由匹配黑名单: {reason} -> {pattern}",
                        "加群申请处理",
                    )
                    return True, reject_reason
            except re.error as e:
                logger.error(
                    f"黑名单正则表达式错误: {e}, pattern: {pattern}",
                    "加群申请处理",
                )
                continue

        return False, None

    async def check_join_reason(self, group_id: str, reason: str) -> bool:
        """
        使用正则表达式检查加群理由（支持多条规则，任意一条匹配即通过）

        Args:
            group_id: 群号
            reason: 加群理由

        Returns:
            是否符合要求
        """
        # 获取群专属的正则表达式列表
        patterns = await self.data_manager.get_pattern(group_id)

        # 如果没有设置群专属规则，使用全局规则
        if not patterns:
            global_pattern = Config.get_config(
                "group_request_handler", "JOIN_REASON_PATTERN"
            )
            patterns = [global_pattern]

        # 检查是否匹配任意一条规则
        for pattern in patterns:
            try:
                # 使用 re.DOTALL 标志让 . 可以匹配换行符
                if re.match(pattern, reason, re.DOTALL):
                    logger.info(
                        f"加群理由匹配规则: {reason} -> {pattern}",
                        "加群申请处理",
                    )
                    return True
            except re.error as e:
                logger.error(
                    f"正则表达式错误: {e}, pattern: {pattern}",
                    "加群申请处理",
                )
                continue

        return False

    async def is_group_in_whitelist(self, group_id: str) -> bool:
        """
        检查群是否在白名单中

        Args:
            group_id: 群号

        Returns:
            是否在白名单中
        """
        return await self.data_manager.is_in_whitelist(group_id)

    async def get_notify_users(self, group_id: str) -> list[str]:
        """
        获取指定群的提醒用户列表

        Args:
            group_id: 群号

        Returns:
            用户QQ号列表
        """
        return await self.data_manager.get_notify_users(group_id)

    async def handle_request(
        self,
        bot: Bot,
        user_id: int,
        group_id: int,
        flag: str,
        comment: str,
        nickname: str,
    ) -> tuple[Literal["approve", "reject", "notify", "ignore"], str | None]:
        """
        处理加群申请

        Args:
            bot: Bot实例
            user_id: 申请人QQ号
            group_id: 群号
            flag: 请求标识
            comment: 加群理由
            nickname: 申请人昵称

        Returns:
            (处理结果, 拒绝理由):
            - approve(同意), reject(拒绝), notify(提醒管理员), ignore(忽略)
            - 拒绝理由(仅当reject时有效)
        """
        group_id_str = str(group_id)

        # 检查是否启用
        if not Config.get_config("group_request_handler", "ENABLED"):
            logger.debug("加群申请处理未启用", "加群申请处理")
            return "ignore", None

        # 检查群是否在白名单中
        if not await self.is_group_in_whitelist(group_id_str):
            logger.debug(
                f"群 {group_id} 不在白名单中,忽略处理",
                "加群申请处理",
                target=group_id,
            )
            return "ignore", None

        # 获取QQ等级
        qq_level = await self.get_qq_level(bot, user_id)
        logger.info(
            f"用户 {nickname}({user_id}) 申请加入群 {group_id}, QQ等级: {qq_level}, 理由: {comment}",
            "加群申请处理",
            session=user_id,
            target=group_id,
        )

        # 检查QQ等级
        if not await self.check_qq_level(group_id_str, qq_level):
            # 获取实际使用的最低等级（群专属或全局）
            min_level = await self.data_manager.get_min_level(group_id_str)
            if min_level is None:
                min_level = Config.get_config("group_request_handler", "MIN_QQ_LEVEL")

            logger.info(
                f"用户 {nickname}({user_id}) QQ等级({qq_level})低于设定值({min_level}),拒绝申请",
                "加群申请处理",
                session=user_id,
                target=group_id,
            )
            # 拒绝申请
            try:
                reject_reason = Config.get_config(
                    "group_request_handler", "REJECT_REASON"
                )
                await bot.set_group_add_request(
                    flag=flag,
                    sub_type="add",
                    approve=False,
                    reason=reject_reason,
                )
                # 记录统计和日志
                await self.data_manager.increment_rejected(group_id_str)
                await self.data_manager.add_request_log(
                    group_id=group_id_str,
                    user_id=user_id,
                    nickname=nickname,
                    comment=comment,
                    action="reject",
                    level=qq_level,
                    reason=reject_reason
                )
                return "reject", reject_reason
            except Exception as e:
                logger.error(
                    f"拒绝加群申请失败: {e}",
                    "加群申请处理",
                    session=user_id,
                    target=group_id,
                    e=e,
                )
                return "ignore", None

        # 检查黑名单
        is_blacklisted, blacklist_reason = await self.check_blacklist(group_id_str, comment)
        if is_blacklisted:
            logger.info(
                f"用户 {nickname}({user_id}) 加群理由匹配黑名单,自动拒绝",
                "加群申请处理",
                session=user_id,
                target=group_id,
            )
            try:
                await bot.set_group_add_request(
                    flag=flag,
                    sub_type="add",
                    approve=False,
                    reason=blacklist_reason or "加群理由不符合要求",
                )
                # 记录统计和日志
                await self.data_manager.increment_rejected(group_id_str)
                await self.data_manager.add_request_log(
                    group_id=group_id_str,
                    user_id=user_id,
                    nickname=nickname,
                    comment=comment,
                    action="reject",
                    level=qq_level,
                    reason=blacklist_reason or "匹配黑名单"
                )
                return "reject", blacklist_reason
            except Exception as e:
                logger.error(
                    f"拒绝加群申请失败: {e}",
                    "加群申请处理",
                    session=user_id,
                    target=group_id,
                    e=e,
                )
                return "ignore", None

        # 检查加群理由
        if not await self.check_join_reason(group_id_str, comment):
            logger.info(
                f"用户 {nickname}({user_id}) 加群理由不符合要求,需要管理员审核",
                "加群申请处理",
                session=user_id,
                target=group_id,
            )
            # 获取提醒用户列表
            notify_users = await self.get_notify_users(group_id_str)
            if notify_users:
                return "notify", None
            else:
                logger.warning(
                    f"群 {group_id} 未配置提醒用户",
                    "加群申请处理",
                    target=group_id,
                )
                return "ignore", None

        # 所有检查都通过
        # 如果启用了自动同意，则同意申请
        if Config.get_config("group_request_handler", "AUTO_APPROVE"):
            logger.info(
                f"用户 {nickname}({user_id}) 通过所有检查,自动同意加群",
                "加群申请处理",
                session=user_id,
                target=group_id,
            )
            try:
                await bot.set_group_add_request(flag=flag, sub_type="add", approve=True)
                # 记录统计和日志
                await self.data_manager.increment_approved(group_id_str)
                await self.data_manager.add_request_log(
                    group_id=group_id_str,
                    user_id=user_id,
                    nickname=nickname,
                    comment=comment,
                    action="approve",
                    level=qq_level
                )
                return "approve", None
            except Exception as e:
                logger.error(
                    f"同意加群申请失败: {e}",
                    "加群申请处理",
                    session=user_id,
                    target=group_id,
                    e=e,
                )
                return "ignore", None
        else:
            # 不自动同意，提醒管理员
            logger.info(
                f"用户 {nickname}({user_id}) 通过所有检查,但未启用自动同意,提醒管理员",
                "加群申请处理",
                session=user_id,
                target=group_id,
            )
            notify_users = await self.get_notify_users(group_id_str)
            if notify_users:
                return "notify", None
            else:
                return "ignore", None
