"""数据管理模块"""

import json
from pathlib import Path

from zhenxun.configs.path_config import DATA_PATH
from zhenxun.services.log import logger


class GroupRequestDataManager:
    """加群申请数据管理器"""

    def __init__(self):
        """初始化数据管理器"""
        self.data_dir = DATA_PATH / "group_request_handler"
        self.whitelist_file = self.data_dir / "whitelist.json"
        self.notify_users_file = self.data_dir / "notify_users.json"
        self.patterns_file = self.data_dir / "patterns.json"
        self.min_levels_file = self.data_dir / "min_levels.json"
        self.pending_requests_file = self.data_dir / "pending_requests.json"
        self.blacklist_file = self.data_dir / "blacklist.json"
        self.statistics_file = self.data_dir / "statistics.json"
        self.request_logs_file = self.data_dir / "request_logs.json"
        self._ensure_data_files()

        # 缓存
        self._whitelist_cache: set[str] | None = None
        self._notify_users_cache: dict[str, list[str]] | None = None
        self._patterns_cache: dict[str, list[str]] | None = None
        self._min_levels_cache: dict[str, int] | None = None
        self._blacklist_cache: dict[str, list[dict]] | None = None
        self._statistics_cache: dict[str, dict] | None = None

    def _ensure_data_files(self):
        """确保数据文件存在"""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        if not self.whitelist_file.exists():
            self.whitelist_file.write_text("[]", encoding="utf-8")

        if not self.notify_users_file.exists():
            self.notify_users_file.write_text("{}", encoding="utf-8")

        if not self.patterns_file.exists():
            self.patterns_file.write_text("{}", encoding="utf-8")

        if not self.min_levels_file.exists():
            self.min_levels_file.write_text("{}", encoding="utf-8")

        if not self.pending_requests_file.exists():
            self.pending_requests_file.write_text("{}", encoding="utf-8")

        if not self.blacklist_file.exists():
            self.blacklist_file.write_text("{}", encoding="utf-8")

        if not self.statistics_file.exists():
            self.statistics_file.write_text("{}", encoding="utf-8")

        if not self.request_logs_file.exists():
            self.request_logs_file.write_text("[]", encoding="utf-8")

    def _load_whitelist(self) -> set[str]:
        """加载群白名单"""
        try:
            data = json.loads(self.whitelist_file.read_text(encoding="utf-8"))
            return set(data)
        except Exception as e:
            logger.error(f"加载群白名单失败: {e}", "加群申请处理")
            return set()

    def _save_whitelist(self, whitelist: set[str]):
        """保存群白名单"""
        try:
            self.whitelist_file.write_text(
                json.dumps(list(whitelist), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            self._whitelist_cache = whitelist.copy()
        except Exception as e:
            logger.error(f"保存群白名单失败: {e}", "加群申请处理")

    def _load_notify_users(self) -> dict[str, list[str]]:
        """加载提醒用户配置"""
        try:
            data = json.loads(self.notify_users_file.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.error(f"加载提醒用户配置失败: {e}", "加群申请处理")
            return {}

    def _save_notify_users(self, notify_users: dict[str, list[str]]):
        """保存提醒用户配置"""
        try:
            self.notify_users_file.write_text(
                json.dumps(notify_users, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            self._notify_users_cache = notify_users.copy()
        except Exception as e:
            logger.error(f"保存提醒用户配置失败: {e}", "加群申请处理")

    def _load_patterns(self) -> dict[str, list[str]]:
        """加载正则表达式配置"""
        try:
            data = json.loads(self.patterns_file.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.error(f"加载正则表达式配置失败: {e}", "加群申请处理")
            return {}

    def _save_patterns(self, patterns: dict[str, list[str]]):
        """保存正则表达式配置"""
        try:
            self.patterns_file.write_text(
                json.dumps(patterns, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            self._patterns_cache = patterns.copy()
        except Exception as e:
            logger.error(f"保存正则表达式配置失败: {e}", "加群申请处理")

    async def get_whitelist(self) -> set[str]:
        """获取群白名单"""
        # 每次都从文件中加载最新数据
        whitelist = self._load_whitelist()
        # 更新缓存
        self._whitelist_cache = whitelist.copy()
        return whitelist

    async def add_to_whitelist(self, group_id: str) -> bool:
        """添加群到白名单"""
        whitelist = await self.get_whitelist()
        if group_id in whitelist:
            return False
        whitelist.add(group_id)
        self._save_whitelist(whitelist)
        return True

    async def remove_from_whitelist(self, group_id: str) -> bool:
        """从白名单移除群"""
        whitelist = await self.get_whitelist()
        if group_id not in whitelist:
            return False
        whitelist.remove(group_id)
        self._save_whitelist(whitelist)
        return True

    async def is_in_whitelist(self, group_id: str) -> bool:
        """检查群是否在白名单中"""
        whitelist = await self.get_whitelist()
        # 如果白名单为空，处理所有群
        if not whitelist:
            return True
        return group_id in whitelist

    async def get_notify_users(self, group_id: str) -> list[str]:
        """获取群的提醒用户列表"""
        # 每次都从文件中加载最新数据
        notify_users = self._load_notify_users()
        # 更新缓存
        self._notify_users_cache = notify_users.copy()
        return notify_users.get(group_id, [])

    async def set_notify_users(self, group_id: str, user_ids: list[str]):
        """设置群的提醒用户列表"""
        # 从文件加载最新数据
        notify_users = self._load_notify_users()
        notify_users[group_id] = user_ids
        self._save_notify_users(notify_users)

    async def add_notify_user(self, group_id: str, user_id: str) -> bool:
        """添加提醒用户"""
        # 从文件加载最新数据
        notify_users = self._load_notify_users()

        if group_id not in notify_users:
            notify_users[group_id] = []

        if user_id in notify_users[group_id]:
            return False

        notify_users[group_id].append(user_id)
        self._save_notify_users(notify_users)
        return True

    async def remove_notify_user(self, group_id: str, user_id: str) -> bool:
        """移除提醒用户"""
        # 从文件加载最新数据
        notify_users = self._load_notify_users()

        if group_id not in notify_users:
            return False

        if user_id not in notify_users[group_id]:
            return False

        notify_users[group_id].remove(user_id)
        self._save_notify_users(notify_users)
        return True

    async def get_pattern(self, group_id: str) -> list[str]:
        """获取群的正则表达式列表

        Args:
            group_id: 群号

        Returns:
            正则表达式列表，如果没有则返回空列表
        """
        # 每次都从文件中加载最新数据
        patterns = self._load_patterns()
        # 更新缓存
        self._patterns_cache = patterns.copy()
        return patterns.get(group_id, [])

    async def add_pattern(self, group_id: str, pattern: str) -> bool:
        """添加加群理由正则表达式

        Args:
            group_id: 群号
            pattern: 正则表达式

        Returns:
            是否成功添加（如果已存在则返回False）
        """
        # 从文件加载最新数据
        patterns = self._load_patterns()

        if group_id not in patterns:
            patterns[group_id] = []

        # 检查是否已存在
        if pattern in patterns[group_id]:
            return False

        patterns[group_id].append(pattern)
        self._save_patterns(patterns)
        return True

    async def remove_pattern_by_index(self, group_id: str, index: int) -> bool:
        """删除指定索引的加群理由规则

        Args:
            group_id: 群号
            index: 索引（从1开始）

        Returns:
            是否成功删除
        """
        # 从文件加载最新数据
        patterns = self._load_patterns()

        if group_id not in patterns:
            return False

        pattern_list = patterns[group_id]

        # 转换为从0开始的索引
        idx = index - 1

        if idx < 0 or idx >= len(pattern_list):
            return False

        pattern_list.pop(idx)
        self._save_patterns(patterns)
        return True

    async def clear_patterns(self, group_id: str) -> bool:
        """清空群的所有正则表达式规则

        Args:
            group_id: 群号

        Returns:
            是否成功清空
        """
        # 从文件加载最新数据
        patterns = self._load_patterns()

        if group_id not in patterns:
            return False

        del patterns[group_id]
        self._save_patterns(patterns)
        return True

    def _load_min_levels(self) -> dict[str, int]:
        """加载最低QQ等级配置"""
        try:
            data = json.loads(self.min_levels_file.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.error(f"加载最低QQ等级配置失败: {e}", "加群申请处理")
            return {}

    def _save_min_levels(self, min_levels: dict[str, int]):
        """保存最低QQ等级配置"""
        try:
            self.min_levels_file.write_text(
                json.dumps(min_levels, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            self._min_levels_cache = min_levels.copy()
        except Exception as e:
            logger.error(f"保存最低QQ等级配置失败: {e}", "加群申请处理")

    async def get_min_level(self, group_id: str) -> int | None:
        """获取群的最低QQ等级要求

        Args:
            group_id: 群号

        Returns:
            最低QQ等级，如果没有设置则返回None
        """
        # 每次都从文件中加载最新数据
        min_levels = self._load_min_levels()
        # 更新缓存
        self._min_levels_cache = min_levels.copy()
        return min_levels.get(group_id)

    async def set_min_level(self, group_id: str, level: int):
        """设置群的最低QQ等级要求

        Args:
            group_id: 群号
            level: 最低QQ等级
        """
        # 从文件加载最新数据
        min_levels = self._load_min_levels()
        min_levels[group_id] = level
        self._save_min_levels(min_levels)

    async def remove_min_level(self, group_id: str) -> bool:
        """移除群的最低QQ等级要求

        Args:
            group_id: 群号

        Returns:
            是否成功移除
        """
        # 从文件加载最新数据
        min_levels = self._load_min_levels()

        if group_id not in min_levels:
            return False

        del min_levels[group_id]
        self._save_min_levels(min_levels)
        return True

    def _load_pending_requests(self) -> dict[str, dict]:
        """加载待处理的加群申请

        Returns:
            字典格式: {message_id: {user_id, group_id, flag, nickname, comment, timestamp}}
        """
        try:
            data = json.loads(self.pending_requests_file.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.error(f"加载待处理申请失败: {e}", "加群申请处理")
            return {}

    def _save_pending_requests(self, pending_requests: dict[str, dict]):
        """保存待处理的加群申请"""
        try:
            self.pending_requests_file.write_text(
                json.dumps(pending_requests, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"保存待处理申请失败: {e}", "加群申请处理")

    async def add_pending_request(
        self,
        message_id: str,
        user_id: int,
        group_id: int,
        flag: str,
        nickname: str,
        comment: str,
        qq_level: int = 0
    ):
        """添加待处理的加群申请

        Args:
            message_id: 通知消息的消息ID
            user_id: 申请人QQ号
            group_id: 群号
            flag: 请求标识
            nickname: 申请人昵称
            comment: 加群理由
            qq_level: QQ等级
        """
        import time

        pending_requests = self._load_pending_requests()
        pending_requests[message_id] = {
            "user_id": user_id,
            "group_id": group_id,
            "flag": flag,
            "nickname": nickname,
            "comment": comment,
            "qq_level": qq_level,
            "timestamp": int(time.time()),
            "notified": True  # 标记已通知用户
        }
        self._save_pending_requests(pending_requests)

    async def get_pending_request(self, message_id: str) -> dict | None:
        """获取待处理的加群申请

        Args:
            message_id: 通知消息的消息ID

        Returns:
            申请信息字典,如果不存在则返回None
        """
        pending_requests = self._load_pending_requests()
        return pending_requests.get(message_id)

    async def remove_pending_request(self, message_id: str) -> bool:
        """移除已处理的加群申请

        Args:
            message_id: 通知消息的消息ID

        Returns:
            是否成功移除
        """
        pending_requests = self._load_pending_requests()
        if message_id not in pending_requests:
            return False

        del pending_requests[message_id]
        self._save_pending_requests(pending_requests)
        return True

    async def clean_expired_requests(self, expire_hours: int = 24):
        """清理过期的待处理申请

        Args:
            expire_hours: 过期时间(小时)
        """
        import time

        pending_requests = self._load_pending_requests()
        current_time = int(time.time())
        expire_seconds = expire_hours * 3600

        expired_ids = [
            msg_id for msg_id, info in pending_requests.items()
            if current_time - info.get("timestamp", 0) > expire_seconds
        ]

        for msg_id in expired_ids:
            del pending_requests[msg_id]

        if expired_ids:
            self._save_pending_requests(pending_requests)
            logger.info(
                f"清理了 {len(expired_ids)} 条过期的加群申请记录",
                "加群申请处理"
            )

    async def get_timeout_requests(self, timeout_seconds: int = 180) -> list[tuple[str, dict]]:
        """获取超时未处理的申请

        Args:
            timeout_seconds: 超时时间(秒)，默认180秒(3分钟)

        Returns:
            超时的申请列表 [(message_id, request_info)]
        """
        import time

        pending_requests = self._load_pending_requests()
        current_time = int(time.time())

        timeout_list = []
        for msg_id, info in pending_requests.items():
            # 检查是否超时且已通知过用户
            if (info.get("notified", False) and
                current_time - info.get("timestamp", 0) >= timeout_seconds):
                timeout_list.append((msg_id, info))

        return timeout_list

    # ==================== 黑名单管理 ====================

    def _load_blacklist(self) -> dict[str, list[dict]]:
        """加载黑名单配置

        Returns:
            字典格式: {群号: [{"pattern": "正则", "reason": "理由"}]}
        """
        try:
            data = json.loads(self.blacklist_file.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.error(f"加载黑名单配置失败: {e}", "加群申请处理")
            return {}

    def _save_blacklist(self, blacklist: dict[str, list[dict]]):
        """保存黑名单配置"""
        try:
            self.blacklist_file.write_text(
                json.dumps(blacklist, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            self._blacklist_cache = {k: v.copy() for k, v in blacklist.items()}
        except Exception as e:
            logger.error(f"保存黑名单配置失败: {e}", "加群申请处理")

    async def get_blacklist(self, group_id: str) -> list[dict]:
        """获取群的黑名单规则列表

        Args:
            group_id: 群号

        Returns:
            黑名单规则列表 [{"pattern": "正则", "reason": "理由"}]
        """
        blacklist = self._load_blacklist()
        self._blacklist_cache = {k: v.copy() for k, v in blacklist.items()}
        return blacklist.get(group_id, [])

    async def add_blacklist_pattern(
        self, group_id: str, pattern: str, reason: str
    ) -> bool:
        """添加黑名单规则

        Args:
            group_id: 群号
            pattern: 正则表达式
            reason: 拒绝理由

        Returns:
            是否成功添加
        """
        blacklist = self._load_blacklist()

        if group_id not in blacklist:
            blacklist[group_id] = []

        # 检查是否已存在相同的正则
        for item in blacklist[group_id]:
            if item["pattern"] == pattern:
                return False

        blacklist[group_id].append({"pattern": pattern, "reason": reason})
        self._save_blacklist(blacklist)
        return True

    async def remove_blacklist_by_index(self, group_id: str, index: int) -> bool:
        """删除指定索引的黑名单规则

        Args:
            group_id: 群号
            index: 索引(从1开始)

        Returns:
            是否成功删除
        """
        blacklist = self._load_blacklist()

        if group_id not in blacklist:
            return False

        blacklist_list = blacklist[group_id]
        idx = index - 1

        if idx < 0 or idx >= len(blacklist_list):
            return False

        blacklist_list.pop(idx)
        self._save_blacklist(blacklist)
        return True

    async def clear_blacklist(self, group_id: str) -> bool:
        """清空群的所有黑名单规则

        Args:
            group_id: 群号

        Returns:
            是否成功清空
        """
        blacklist = self._load_blacklist()

        if group_id not in blacklist:
            return False

        del blacklist[group_id]
        self._save_blacklist(blacklist)
        return True

    # ==================== 统计管理 ====================

    def _load_statistics(self) -> dict[str, dict]:
        """加载统计数据

        Returns:
            字典格式: {群号: {"approved": 数量, "rejected": 数量, "ai_approved": 数量, "ai_rejected": 数量}}
        """
        try:
            data = json.loads(self.statistics_file.read_text(encoding="utf-8"))
            # 向后兼容：为旧数据补充AI统计字段
            for group_id, stats in data.items():
                if "ai_approved" not in stats:
                    stats["ai_approved"] = 0
                if "ai_rejected" not in stats:
                    stats["ai_rejected"] = 0
            return data
        except Exception as e:
            logger.error(f"加载统计数据失败: {e}", "加群申请处理")
            return {}

    def _save_statistics(self, statistics: dict[str, dict]):
        """保存统计数据"""
        try:
            self.statistics_file.write_text(
                json.dumps(statistics, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            self._statistics_cache = {k: v.copy() for k, v in statistics.items()}
        except Exception as e:
            logger.error(f"保存统计数据失败: {e}", "加群申请处理")

    async def get_statistics(self, group_id: str) -> dict:
        """获取群的统计数据

        Args:
            group_id: 群号

        Returns:
            统计数据 {"approved": 数量, "rejected": 数量, "ai_approved": 数量, "ai_rejected": 数量}
        """
        statistics = self._load_statistics()
        self._statistics_cache = {k: v.copy() for k, v in statistics.items()}
        return statistics.get(group_id, {"approved": 0, "rejected": 0, "ai_approved": 0, "ai_rejected": 0})

    async def get_all_statistics(self) -> dict[str, dict]:
        """获取所有群的统计数据

        Returns:
            所有统计数据 {群号: {"approved": 数量, "rejected": 数量, "ai_approved": 数量, "ai_rejected": 数量}}
        """
        statistics = self._load_statistics()
        self._statistics_cache = {k: v.copy() for k, v in statistics.items()}
        return statistics

    async def increment_approved(self, group_id: str):
        """增加同意计数

        Args:
            group_id: 群号
        """
        statistics = self._load_statistics()

        if group_id not in statistics:
            statistics[group_id] = {"approved": 0, "rejected": 0, "ai_approved": 0, "ai_rejected": 0}

        statistics[group_id]["approved"] += 1
        self._save_statistics(statistics)

    async def increment_rejected(self, group_id: str):
        """增加拒绝计数

        Args:
            group_id: 群号
        """
        statistics = self._load_statistics()

        if group_id not in statistics:
            statistics[group_id] = {"approved": 0, "rejected": 0, "ai_approved": 0, "ai_rejected": 0}

        statistics[group_id]["rejected"] += 1
        self._save_statistics(statistics)

    async def increment_ai_approved(self, group_id: str):
        """增加AI同意计数

        Args:
            group_id: 群号
        """
        statistics = self._load_statistics()

        if group_id not in statistics:
            statistics[group_id] = {"approved": 0, "rejected": 0, "ai_approved": 0, "ai_rejected": 0}

        statistics[group_id]["ai_approved"] += 1
        self._save_statistics(statistics)

    async def increment_ai_rejected(self, group_id: str):
        """增加AI拒绝计数

        Args:
            group_id: 群号
        """
        statistics = self._load_statistics()

        if group_id not in statistics:
            statistics[group_id] = {"approved": 0, "rejected": 0, "ai_approved": 0, "ai_rejected": 0}

        statistics[group_id]["ai_rejected"] += 1
        self._save_statistics(statistics)

    # ==================== 日志管理 ====================

    def _load_request_logs(self) -> list[dict]:
        """加载请求日志

        Returns:
            日志列表
        """
        try:
            data = json.loads(self.request_logs_file.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.error(f"加载请求日志失败: {e}", "加群申请处理")
            return []

    def _save_request_logs(self, logs: list[dict]):
        """保存请求日志"""
        try:
            self.request_logs_file.write_text(
                json.dumps(logs, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"保存请求日志失败: {e}", "加群申请处理")

    async def add_request_log(
        self,
        group_id: str,
        user_id: int,
        nickname: str,
        comment: str,
        action: str,
        level: int,
        reason: str | None = None,
        is_ai_reviewed: bool = False
    ):
        """添加请求日志

        Args:
            group_id: 群号
            user_id: 申请人QQ号
            nickname: 昵称
            comment: 加群理由
            action: 操作 approve/reject
            level: QQ等级
            reason: 拒绝理由(可选)
            is_ai_reviewed: 是否为AI审核(可选)
        """
        from datetime import datetime

        logs = self._load_request_logs()

        log_entry = {
            "group_id": group_id,
            "user_id": user_id,
            "nickname": nickname,
            "comment": comment,
            "action": action,
            "level": level,
            "timestamp": datetime.now().isoformat()
        }

        if reason:
            log_entry["reason"] = reason

        if is_ai_reviewed:
            log_entry["is_ai_reviewed"] = True

        logs.append(log_entry)

        # 限制日志数量,保留最近1000条
        if len(logs) > 1000:
            logs = logs[-1000:]

        self._save_request_logs(logs)

    async def get_request_logs(
        self, group_id: str | None = None, limit: int = 10
    ) -> list[dict]:
        """获取请求日志

        Args:
            group_id: 群号(可选,不指定则返回所有)
            limit: 返回数量限制

        Returns:
            日志列表(按时间倒序)
        """
        logs = self._load_request_logs()

        # 筛选指定群的日志
        if group_id:
            logs = [log for log in logs if log.get("group_id") == group_id]

        # 按时间倒序排序并限制数量
        logs.reverse()
        return logs[:limit]

    async def get_user_approved_request(
        self, user_id: str, group_id: str
    ) -> dict | None:
        """获取指定用户在指定群的通过记录

        Args:
            user_id: 用户QQ号
            group_id: 群号

        Returns:
            通过记录详情字典,如果未找到则返回None
        """
        logs = self._load_request_logs()

        # 筛选指定用户和群组的通过记录(action="approve")
        # 按时间倒序查找,返回最近的一条
        for log in reversed(logs):
            if (
                str(log.get("user_id")) == str(user_id)
                and log.get("group_id") == str(group_id)
                and log.get("action") == "approve"
            ):
                return log

        return None
