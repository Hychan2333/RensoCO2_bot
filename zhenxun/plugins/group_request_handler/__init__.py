"""加群申请处理插件"""

import asyncio
import re

from nonebot import on_request, on_message, require
from nonebot.adapters.onebot.v11 import Bot, GroupRequestEvent, MessageEvent, PrivateMessageEvent
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import Alconna, Args, Arparma, Match, on_alconna
from nonebot_plugin_uninfo import Uninfo

from zhenxun.configs.config import Config
from zhenxun.configs.utils import PluginExtraData, RegisterConfig
from zhenxun.services.log import logger
from zhenxun.utils.enum import PluginType
from zhenxun.utils.message import MessageUtils
from zhenxun.utils.rules import admin_check

from .data_manager import GroupRequestDataManager
from .data_source import GroupRequestHandler
from .ai_reviewer import analyze_join_request

# 定时任务支持
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

# 输出插件加载信息
logger.info("加群申请处理插件已加载", "加群申请处理")

__plugin_meta__ = PluginMetadata(
    name="加群申请处理",
    description="自动处理群白名单内的加群申请,根据QQ等级、黑名单和加群理由进行审核,支持统计查询",
    usage="""
    自动处理加群申请，支持QQ等级过滤、黑名单过滤和加群理由验证

    群内管理命令（管理员）：
    【白名单管理】
    加群白名单              : 查看当前群是否在白名单中
    添加加群白名单          : 将当前群添加到白名单
    移除加群白名单          : 将当前群从白名单移除

    【提醒用户管理】
    加群提醒列表            : 查看当前群的提醒用户列表
    添加加群提醒 [QQ号]     : 添加提醒用户
    移除加群提醒 [QQ号]     : 移除提醒用户

    【白名单规则】
    添加加群理由规则 [正则]  : 添加当前群的加群理由验证规则(白名单)
    删除加群理由规则 [索引]  : 删除指定的白名单规则
    查看加群理由规则        : 查看当前群的白名单规则列表
    清空加群理由规则        : 清空当前群的所有白名单规则

    【黑名单规则】
    添加加群黑名单 [正则] [拒绝理由]  : 添加黑名单规则,匹配后自动拒绝
    删除加群黑名单 [索引]            : 删除指定的黑名单规则
    查看加群黑名单                  : 查看当前群的黑名单规则列表
    清空加群黑名单                  : 清空当前群的所有黑名单规则

    【统计查询】
    加群统计 [数量?]        : 查看本群加群申请统计和最近记录(默认10条,0则不显示)
    AI审核统计 [群号?]      : 查看AI审核统计(群聊查看本群,私聊可指定群号或查看全部)
    加群处理状态           : 查看当前配置状态

    申请通知机制：
    当有加群申请需要审核时，系统会私聊通知所有提醒用户
    管理员可以直接回复Bot的通知消息来处理申请：
        回复 "同意" - 同意该申请
        回复 "拒绝 [理由]" - 拒绝该申请(可选填理由)

    私聊管理命令（超级用户）：
    加群管理帮助                              : 查看私聊管理命令帮助
    加群白名单列表                            : 查看所有群的白名单状态
    查看加群状态 [群号]                       : 查看指定群的配置
    添加加群白名单 [群号]                     : 添加群到白名单
    移除加群白名单 [群号]                     : 移除群白名单
    设置加群提醒 [群号] [QQ号列表]            : 设置群的提醒用户(逗号分隔)
    设置最低等级 [群号] [等级]                : 设置群的最低QQ等级要求
    移除最低等级 [群号]                       : 移除群的专属等级要求
    添加加群规则 [群号] [正则]                : 添加群的白名单规则
    删除加群规则 [群号] [索引]                : 删除群的白名单规则
    清空加群规则 [群号]                       : 清空群的白名单规则
    添加加群黑名单 [群号] [正则] [理由]       : 添加群的黑名单规则
    删除加群黑名单 [群号] [索引]              : 删除群的黑名单规则
    清空加群黑名单 [群号]                     : 清空群的黑名单规则
    查看加群统计 [群号?]                      : 查看统计(不指定群号则查看所有群)
    AI审核统计 [群号?]                        : 查看AI审核统计(不指定群号则查看所有群)
    查看加群日志 [群号] [数量?]               : 查看指定群的详细日志(默认10条)
    查询用户申请 [QQ号] [群号]                : 查询指定用户在指定群的通过记录

    示例：
        【群内】
        添加加群白名单
        添加加群提醒 123456789
        添加加群理由规则 ^邀请码:[A-Z0-9]{6}$
        添加加群黑名单 .*垃圾.* 加群理由包含不当内容
        加群统计        (显示统计和最近10条记录)
        加群统计 0      (只显示统计,不显示记录)
        加群统计 20     (显示统计和最近20条记录)
        AI审核统计      (显示本群AI审核统计)
        加群处理状态

        【私聊】
        加群管理帮助
        查看加群统计
        查看加群统计 123456789
        AI审核统计
        AI审核统计 123456789
        查看加群日志 123456789 20
        查询用户申请 123456 789012345
        添加加群黑名单 123456789 .*广告.* 禁止广告
    """.strip(),
    extra=PluginExtraData(
        author="BingZi-233",
        version="0.5.0",
        plugin_type=PluginType.ADMIN,
        configs=[
            RegisterConfig(
                module="group_request_handler",
                key="ENABLED",
                value=True,
                help="是否启用加群申请处理",
                default_value=True,
                type=bool,
            ),
            RegisterConfig(
                module="group_request_handler",
                key="MIN_QQ_LEVEL",
                value=16,
                help="最低QQ等级要求",
                default_value=16,
                type=int,
            ),
            RegisterConfig(
                module="group_request_handler",
                key="REJECT_REASON",
                value="抱歉,您的QQ等级过低,暂时无法加入本群",
                help="QQ等级不足时的拒绝理由",
                default_value="抱歉,您的QQ等级过低,暂时无法加入本群",
                type=str,
            ),
            RegisterConfig(
                module="group_request_handler",
                key="JOIN_REASON_PATTERN",
                value=r".*\d{6,}.*",
                help="加群理由的正则表达式(默认要求包含6位以上数字)",
                default_value=r".*\d{6,}.*",
                type=str,
            ),
            RegisterConfig(
                module="group_request_handler",
                key="AUTO_APPROVE",
                value=True,
                help="通过所有检查后是否自动同意(false则提醒管理员)",
                default_value=True,
                type=bool,
            ),
            RegisterConfig(
                module="group_request_handler",
                key="AI_AUTO_REVIEW_ENABLED",
                value=True,
                help="是否启用AI自动审核(3分钟无人处理后使用AI拒绝不合格申请,AI无批准权限)",
                default_value=True,
                type=bool,
            ),
            RegisterConfig(
                module="group_request_handler",
                key="AI_REVIEW_TIMEOUT",
                value=180,
                help="AI自动审核超时时间(秒)，默认180秒(3分钟)",
                default_value=180,
                type=int,
            ),
            RegisterConfig(
                module="group_request_handler",
                key="AI_REVIEW_MODEL",
                value=None,
                help="AI审核使用的模型(格式: Provider/Model)，留空使用全局默认模型",
                default_value=None,
                type=str,
            ),
            RegisterConfig(
                module="group_request_handler",
                key="AI_MIN_CONFIDENCE",
                value=0.8,
                help="AI审核最低置信度(0.0-1.0)，低于此值将不自动处理",
                default_value=0.8,
                type=float,
            ),
        ],
    ).to_dict(),
)

# 初始化数据管理器
data_manager = GroupRequestDataManager()

# 初始化处理器
handler = GroupRequestHandler(data_manager)

# 监听加群请求
group_request = on_request(priority=5, block=False)


@group_request.handle()
async def _(bot: Bot, event: GroupRequestEvent):
    """处理加群申请"""
    # 只处理加群申请,不处理邀请Bot入群
    if event.sub_type != "add":
        return

    user_id = event.user_id
    group_id = event.group_id
    flag = event.flag
    comment = event.comment

    # 获取用户信息
    try:
        user_info = await bot.get_stranger_info(user_id=user_id)
        nickname = user_info.get("nickname", str(user_id))
    except Exception as e:
        logger.error(
            f"获取用户 {user_id} 信息失败: {e}",
            "加群申请处理",
            session=user_id,
            target=group_id,
            e=e,
        )
        nickname = str(user_id)

    # 处理申请
    result, _ = await handler.handle_request(
        bot=bot,
        user_id=user_id,
        group_id=group_id,
        flag=flag,
        comment=comment,
        nickname=nickname,
    )

    # 如果需要提醒管理员
    if result == "notify":
        notify_users = await handler.get_notify_users(str(group_id))
        if notify_users:
            # 构建消息
            qq_level = await handler.get_qq_level(bot, user_id)

            # 私聊通知提醒用户
            private_message = (
                f"【加群申请待审核】\n"
                f"群号: {group_id}\n"
                f"申请人: {nickname}({user_id})\n"
                f"QQ等级: {qq_level}\n"
                f"加群理由: {comment}\n\n"
                f"回复此消息进行处理:\n"
                f"  同意 - 同意该申请\n"
                f"  拒绝 [理由] - 拒绝该申请(可选填理由)"
            )

            for uid in notify_users:
                try:
                    # 发送私聊消息并保存消息ID
                    result_msg = await bot.send_private_msg(
                        user_id=int(uid),
                        message=private_message
                    )

                    # 保存待处理的申请信息
                    message_id = str(result_msg["message_id"])
                    await data_manager.add_pending_request(
                        message_id=message_id,
                        user_id=user_id,
                        group_id=group_id,
                        flag=flag,
                        nickname=nickname,
                        comment=comment,
                        qq_level=qq_level
                    )

                    logger.info(
                        f"已私聊通知用户 {uid} 处理群 {group_id} 的加群申请",
                        "加群申请处理",
                        target=group_id,
                    )
                except Exception as e:
                    logger.error(
                        f"私聊通知用户 {uid} 失败: {e}",
                        "加群申请处理",
                        target=group_id,
                        e=e,
                    )


# ==================== 管理命令 ====================

# 查看白名单状态
check_whitelist = on_alconna(
    Alconna("加群白名单"),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@check_whitelist.handle()
async def _(session: Uninfo):
    """查看白名单状态"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    group_id = session.group.id
    is_in = await data_manager.is_in_whitelist(group_id)

    if is_in:
        await MessageUtils.build_message(
            f"✅ 当前群({group_id})已在加群白名单中\n将会自动处理加群申请"
        ).send()
    else:
        await MessageUtils.build_message(
            f"❌ 当前群({group_id})不在加群白名单中\n使用「添加加群白名单」命令添加"
        ).send()


# 添加白名单
add_whitelist = on_alconna(
    Alconna("添加加群白名单"),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@add_whitelist.handle()
async def _(session: Uninfo):
    """添加白名单"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    group_id = session.group.id
    success = await data_manager.add_to_whitelist(group_id)

    if success:
        logger.info(f"群 {group_id} 已添加到加群白名单", "加群申请处理", target=group_id)
        await MessageUtils.build_message(
            "✅ 已将当前群添加到加群白名单\n现在会自动处理加群申请"
        ).send()
    else:
        await MessageUtils.build_message("❌ 当前群已在白名单中").send()


# 移除白名单
remove_whitelist = on_alconna(
    Alconna("移除加群白名单"),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@remove_whitelist.handle()
async def _(session: Uninfo):
    """移除白名单"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    group_id = session.group.id
    success = await data_manager.remove_from_whitelist(group_id)

    if success:
        logger.info(f"群 {group_id} 已从加群白名单移除", "加群申请处理", target=group_id)
        await MessageUtils.build_message(
            "✅ 已将当前群从加群白名单移除\n将不再自动处理加群申请"
        ).send()
    else:
        await MessageUtils.build_message("❌ 当前群不在白名单中").send()


# 查看提醒用户列表
list_notify_users = on_alconna(
    Alconna("加群提醒列表"),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@list_notify_users.handle()
async def _(session: Uninfo):
    """查看提醒用户列表"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    group_id = session.group.id
    notify_users = await data_manager.get_notify_users(group_id)

    if not notify_users:
        await MessageUtils.build_message(
            "❌ 当前群未配置提醒用户\n使用「添加加群提醒 [QQ号]」命令添加"
        ).send()
        return

    msg_lines = ["【加群提醒用户列表】"]
    for idx, user_id in enumerate(notify_users, 1):
        msg_lines.append(f"{idx}. {user_id}")

    await MessageUtils.build_message("\n".join(msg_lines)).send()


# 添加提醒用户
add_notify_user = on_alconna(
    Alconna("添加加群提醒", Args["user_id", str]),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@add_notify_user.handle()
async def _(session: Uninfo, arparma: Arparma, user_id: Match[str]):
    """添加提醒用户"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    if not user_id.available:
        await MessageUtils.build_message("请提供要添加的QQ号").send()
        return

    group_id = session.group.id
    uid = user_id.result

    success = await data_manager.add_notify_user(group_id, uid)

    if success:
        logger.info(
            f"已为群 {group_id} 添加提醒用户 {uid}", "加群申请处理", target=group_id
        )
        await MessageUtils.build_message(f"✅ 已添加提醒用户: {uid}").send()
    else:
        await MessageUtils.build_message("❌ 该用户已在提醒列表中").send()


# 移除提醒用户
remove_notify_user = on_alconna(
    Alconna("移除加群提醒", Args["user_id", str]),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@remove_notify_user.handle()
async def _(session: Uninfo, arparma: Arparma, user_id: Match[str]):
    """移除提醒用户"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    if not user_id.available:
        await MessageUtils.build_message("请提供要移除的QQ号").send()
        return

    group_id = session.group.id
    uid = user_id.result

    success = await data_manager.remove_notify_user(group_id, uid)

    if success:
        logger.info(
            f"已为群 {group_id} 移除提醒用户 {uid}", "加群申请处理", target=group_id
        )
        await MessageUtils.build_message(f"✅ 已移除提醒用户: {uid}").send()
    else:
        await MessageUtils.build_message("❌ 该用户不在提醒列表中").send()


# 添加加群理由规则
add_pattern = on_alconna(
    Alconna("添加加群理由规则", Args["pattern", str]),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@add_pattern.handle()
async def _(session: Uninfo, arparma: Arparma, pattern: Match[str]):
    """添加加群理由规则"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    if not pattern.available:
        await MessageUtils.build_message("请提供正则表达式").send()
        return

    pattern_str = pattern.result

    # 验证正则表达式
    try:
        re.compile(pattern_str)
    except re.error as e:
        await MessageUtils.build_message(f"❌ 无效的正则表达式: {e}").send()
        return

    group_id = session.group.id
    success = await data_manager.add_pattern(group_id, pattern_str)

    if success:
        logger.info(
            f"已为群 {group_id} 添加加群理由规则: {pattern_str}",
            "加群申请处理",
            target=group_id,
        )
        await MessageUtils.build_message(
            f"✅ 已添加加群理由规则:\n{pattern_str}"
        ).send()
    else:
        await MessageUtils.build_message("❌ 该规则已存在").send()


# 删除加群理由规则
del_pattern = on_alconna(
    Alconna("删除加群理由规则", Args["index", int]),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@del_pattern.handle()
async def _(session: Uninfo, arparma: Arparma, index: Match[int]):
    """删除加群理由规则"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    if not index.available:
        await MessageUtils.build_message("请提供要删除的索引").send()
        return

    index_num = index.result
    group_id = session.group.id

    success = await data_manager.remove_pattern_by_index(group_id, index_num)

    if success:
        logger.info(
            f"已删除群 {group_id} 的加群理由规则索引: {index_num}",
            "加群申请处理",
            target=group_id,
        )
        await MessageUtils.build_message(f"✅ 已删除规则 #{index_num}").send()
    else:
        await MessageUtils.build_message("❌ 删除失败，索引不存在").send()


# 查看加群理由规则
show_pattern = on_alconna(
    Alconna("查看加群理由规则"),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@show_pattern.handle()
async def _(session: Uninfo):
    """查看加群理由规则"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    group_id = session.group.id
    patterns = await data_manager.get_pattern(group_id)

    if patterns:
        msg_lines = ["【当前群加群理由规则】"]
        for idx, pattern in enumerate(patterns, 1):
            msg_lines.append(f"{idx}. {pattern}")
        msg_lines.append("\n(群专属规则)")
        await MessageUtils.build_message("\n".join(msg_lines)).send()
    else:
        global_pattern = Config.get_config(
            "group_request_handler", "JOIN_REASON_PATTERN"
        )
        await MessageUtils.build_message(
            f"【当前群加群理由规则】\n1. {global_pattern}\n\n(全局默认规则)\n\n使用「添加加群理由规则」命令添加专属规则"
        ).send()


# 清空加群理由规则
clear_patterns = on_alconna(
    Alconna("清空加群理由规则"),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@clear_patterns.handle()
async def _(session: Uninfo):
    """清空加群理由规则"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    group_id = session.group.id
    success = await data_manager.clear_patterns(group_id)

    if success:
        logger.info(
            f"已清空群 {group_id} 的加群理由规则", "加群申请处理", target=group_id
        )
        await MessageUtils.build_message(
            "✅ 已清空当前群的所有专属规则\n将使用全局默认规则"
        ).send()
    else:
        await MessageUtils.build_message("❌ 当前群未设置专属规则").send()


# ==================== 黑名单管理命令 ====================

# 添加加群黑名单规则
add_blacklist = on_alconna(
    Alconna("添加加群黑名单", Args["pattern", str]["reason", str]),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@add_blacklist.handle()
async def _(session: Uninfo, pattern: Match[str], reason: Match[str]):
    """添加加群黑名单规则"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    if not pattern.available or not reason.available:
        await MessageUtils.build_message("❌ 请提供正则表达式和拒绝理由\n示例: 添加加群黑名单 .*垃圾.* 加群理由包含不当内容").send()
        return

    group_id = session.group.id
    pattern_str = pattern.result.strip()
    reason_str = reason.result.strip()

    # 验证正则表达式
    try:
        re.compile(pattern_str)
    except re.error as e:
        await MessageUtils.build_message(f"❌ 正则表达式无效: {e}").send()
        return

    success = await data_manager.add_blacklist_pattern(group_id, pattern_str, reason_str)

    if success:
        logger.info(
            f"群 {group_id} 添加了加群黑名单规则: {pattern_str} -> {reason_str}",
            "加群申请处理",
            target=group_id,
        )
        await MessageUtils.build_message(
            f"✅ 已添加黑名单规则\n正则: {pattern_str}\n拒绝理由: {reason_str}"
        ).send()
    else:
        await MessageUtils.build_message("❌ 该规则已存在").send()


# 删除加群黑名单规则
remove_blacklist = on_alconna(
    Alconna("删除加群黑名单", Args["index", int]),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@remove_blacklist.handle()
async def _(session: Uninfo, index: Match[int]):
    """删除加群黑名单规则"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    if not index.available:
        await MessageUtils.build_message("❌ 请提供规则索引\n示例: 删除加群黑名单 1").send()
        return

    group_id = session.group.id
    idx = index.result

    success = await data_manager.remove_blacklist_by_index(group_id, idx)

    if success:
        logger.info(
            f"群 {group_id} 删除了加群黑名单规则 #{idx}", "加群申请处理", target=group_id
        )
        await MessageUtils.build_message(f"✅ 已删除黑名单规则 #{idx}").send()
    else:
        await MessageUtils.build_message("❌ 规则索引不存在").send()


# 查看加群黑名单
view_blacklist = on_alconna(
    Alconna("查看加群黑名单"),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@view_blacklist.handle()
async def _(session: Uninfo):
    """查看加群黑名单"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    group_id = session.group.id
    blacklist = await data_manager.get_blacklist(group_id)

    if not blacklist:
        await MessageUtils.build_message("❌ 当前群未设置黑名单规则").send()
        return

    msg_lines = [f"【加群黑名单规则列表】(共 {len(blacklist)} 条)"]
    for idx, item in enumerate(blacklist, 1):
        pattern = item.get("pattern", "")
        reason = item.get("reason", "")
        msg_lines.append(f"{idx}. 正则: {pattern}")
        msg_lines.append(f"   拒绝理由: {reason}")

    await MessageUtils.build_message("\n".join(msg_lines)).send()


# 清空加群黑名单
clear_blacklist = on_alconna(
    Alconna("清空加群黑名单"),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@clear_blacklist.handle()
async def _(session: Uninfo):
    """清空加群黑名单"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    group_id = session.group.id
    success = await data_manager.clear_blacklist(group_id)

    if success:
        logger.info(
            f"已清空群 {group_id} 的加群黑名单", "加群申请处理", target=group_id
        )
        await MessageUtils.build_message("✅ 已清空当前群的所有黑名单规则").send()
    else:
        await MessageUtils.build_message("❌ 当前群未设置黑名单规则").send()


# ==================== 统计查询命令 ====================

# 查看加群统计
view_statistics = on_alconna(
    Alconna("加群统计", Args["limit?", int]),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@view_statistics.handle()
async def _(session: Uninfo, limit: Match[int]):
    """查看加群统计"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    group_id = session.group.id

    # 获取统计数据
    stats = await data_manager.get_statistics(group_id)
    approved = stats.get("approved", 0)
    rejected = stats.get("rejected", 0)
    ai_approved = stats.get("ai_approved", 0)
    ai_rejected = stats.get("ai_rejected", 0)
    total = approved + rejected

    # 获取日志数量限制,默认10条,如果指定为0则不显示日志
    log_limit = limit.result if limit.available else 10

    msg_lines = [
        "【加群申请统计】",
        f"总处理: {total} 次",
        f"✅ 已同意: {approved} 次",
        f"❌ 已拒绝: {rejected} 次",
    ]

    # 显示AI统计 - AI只能拒绝,不能通过
    if ai_rejected > 0:
        ai_rate = (ai_rejected / total * 100) if total > 0 else 0
        msg_lines.append(f"\n🤖 AI拒绝: {ai_rejected} 次 ({ai_rate:.1f}%)")

    if total > 0:
        approve_rate = (approved / total) * 100
        msg_lines.append(f"\n总通过率: {approve_rate:.1f}%")

    # 显示最近日志(如果log_limit > 0)
    if log_limit > 0:
        logs = await data_manager.get_request_logs(group_id, limit=log_limit)
        if logs:
            msg_lines.append(f"\n【最近 {len(logs)} 条记录】")
            for log in logs:
                action_emoji = "✅" if log["action"] == "approve" else "❌"
                ai_badge = "🤖" if log.get("is_ai_reviewed") else ""
                timestamp = log["timestamp"][:19]  # 截取到秒
                msg_lines.append(
                    f"{action_emoji}{ai_badge} {timestamp} | {log['nickname']}({log['user_id']}) | 等级{log['level']}"
                )
                if log.get("reason"):
                    msg_lines.append(f"   理由: {log['reason']}")

    await MessageUtils.build_message("\n".join(msg_lines)).send()


# AI审核统计
ai_statistics = on_alconna(
    Alconna("AI审核统计", Args["group_id?", str]),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@ai_statistics.handle()
async def _(bot: Bot, session: Uninfo, group_id: Match[str]):
    """查看AI审核统计"""
    # 群聊和私聊都支持
    target_group_id = None

    if session.group:
        # 群聊中使用,查看本群统计
        target_group_id = session.group.id
    else:
        # 私聊中使用,需要超级用户权限
        if session.user.id not in bot.config.superusers:
            await MessageUtils.build_message("❌ 私聊使用该命令需要超级用户权限").send()
            return

        # 如果指定了群号,查看该群;否则查看所有群
        if group_id.available:
            target_group_id = group_id.result

    if target_group_id:
        # 查看单个群的AI统计
        stats = await data_manager.get_statistics(target_group_id)
        approved = stats.get("approved", 0)
        rejected = stats.get("rejected", 0)
        ai_rejected = stats.get("ai_rejected", 0)
        total = approved + rejected

        msg_lines = [f"【群 {target_group_id} AI审核统计】"]

        if ai_rejected == 0:
            msg_lines.append("暂无AI拒绝记录")
        else:
            ai_rate = (ai_rejected / total * 100) if total > 0 else 0

            msg_lines.extend([
                f"\n🤖 AI拒绝总数: {ai_rejected} 次",
                f"AI介入率: {ai_rate:.1f}%",
                f"\n📊 总处理: {total} 次",
                f"人工处理: {total - ai_rejected} 次",
                f"\n⚠️ 注: AI只能拒绝申请,不能批准"
            ])

            # 获取最近的AI审核记录
            all_logs = await data_manager.get_request_logs(target_group_id, limit=50)
            ai_logs = [log for log in all_logs if log.get("is_ai_reviewed")][:5]

            if ai_logs:
                msg_lines.append(f"\n【最近 {len(ai_logs)} 条AI拒绝记录】")
                for log in ai_logs:
                    action_emoji = "❌"  # AI只会拒绝
                    timestamp = log["timestamp"][:19]
                    msg_lines.append(
                        f"{action_emoji} {timestamp} | {log['nickname']}({log['user_id']}) | 等级{log['level']}"
                    )
                    if log.get("reason"):
                        msg_lines.append(f"   {log['reason']}")
    else:
        # 查看所有群的AI统计汇总(仅私聊超级用户)
        all_stats = await data_manager.get_all_statistics()

        if not all_stats:
            await MessageUtils.build_message("❌ 暂无统计数据").send()
            return

        msg_lines = ["【所有群AI审核统计汇总】"]
        total_ai_rejected = 0
        total_approved = 0
        total_rejected = 0
        groups_with_ai = []

        for gid, stats in all_stats.items():
            ai_rejected = stats.get("ai_rejected", 0)
            approved = stats.get("approved", 0)
            rejected = stats.get("rejected", 0)

            if ai_rejected > 0:
                total = approved + rejected
                ai_rate = (ai_rejected / total * 100) if total > 0 else 0
                groups_with_ai.append((gid, ai_rejected, ai_rate))

            total_ai_rejected += ai_rejected
            total_approved += approved
            total_rejected += rejected

        grand_total = total_approved + total_rejected

        if total_ai_rejected == 0:
            msg_lines.append("\n暂无AI拒绝记录")
        else:
            grand_ai_rate = (total_ai_rejected / grand_total * 100) if grand_total > 0 else 0

            msg_lines.extend([
                f"\n🤖 总AI拒绝: {total_ai_rejected} 次",
                f"总介入率: {grand_ai_rate:.1f}%",
                f"\n共 {len(groups_with_ai)} 个群使用了AI拒绝",
                f"\n⚠️ 注: AI只能拒绝申请,不能批准"
            ])

            if groups_with_ai:
                msg_lines.append("\n【各群AI拒绝情况】")
                # 按AI拒绝次数降序排序
                groups_with_ai.sort(key=lambda x: x[1], reverse=True)
                for gid, ai_rej, ai_rt in groups_with_ai[:10]:
                    msg_lines.append(
                        f"群 {gid}: {ai_rej}次 ({ai_rt:.1f}%)"
                    )
                if len(groups_with_ai) > 10:
                    msg_lines.append(f"... 还有 {len(groups_with_ai) - 10} 个群")

        msg_lines.append("\n提示: 使用 'AI审核统计 [群号]' 查看指定群的详细记录")

    await MessageUtils.build_message("\n".join(msg_lines)).send()


# 查看配置状态
show_status = on_alconna(
    Alconna("加群处理状态"),
    rule=admin_check(5),
    priority=5,
    block=True,
)


@show_status.handle()
async def _(session: Uninfo):
    """查看配置状态"""
    if not session.group:
        await MessageUtils.build_message("该命令仅支持群聊使用").send()
        return

    group_id = session.group.id

    # 获取配置
    enabled = Config.get_config("group_request_handler", "ENABLED")
    global_min_level = Config.get_config("group_request_handler", "MIN_QQ_LEVEL")
    auto_approve = Config.get_config("group_request_handler", "AUTO_APPROVE")

    # 获取群数据
    is_in_whitelist = await data_manager.is_in_whitelist(group_id)
    notify_users = await data_manager.get_notify_users(group_id)
    patterns = await data_manager.get_pattern(group_id)
    blacklist = await data_manager.get_blacklist(group_id)
    min_level = await data_manager.get_min_level(group_id)
    stats = await data_manager.get_statistics(group_id)

    # 确定最低等级显示
    if min_level is not None:
        min_level_display = f"{min_level} (专属配置)"
    else:
        min_level_display = f"{global_min_level} (全局配置)"

    if patterns:
        pattern_display = f"{len(patterns)} 条专属规则"
        pattern_type = "(白名单)"
    else:
        pattern_display = "1 条全局规则"
        pattern_type = "(白名单)"

    msg_lines = [
        "【加群申请处理状态】",
        f"全局启用: {'✅ 是' if enabled else '❌ 否'}",
        f"当前群状态: {'✅ 在白名单' if is_in_whitelist else '❌ 不在白名单'}",
        f"最低QQ等级: {min_level_display}",
        f"自动同意: {'✅ 是' if auto_approve else '❌ 否(提醒管理员)'}",
        f"提醒用户数: {len(notify_users)}",
        f"加群理由规则: {pattern_display} {pattern_type}",
        f"黑名单规则: {len(blacklist)} 条",
    ]

    # 统计信息
    approved = stats.get("approved", 0)
    rejected = stats.get("rejected", 0)
    total = approved + rejected
    if total > 0:
        approve_rate = (approved / total) * 100
        msg_lines.append(f"\n【统计信息】")
        msg_lines.append(f"总处理: {total} 次")
        msg_lines.append(f"✅ 同意: {approved} 次 | ❌ 拒绝: {rejected} 次")
        msg_lines.append(f"通过率: {approve_rate:.1f}%")

    # 显示白名单规则详情
    if patterns:
        msg_lines.append("\n【白名单规则列表】")
        for idx, pattern in enumerate(patterns[:3], 1):
            msg_lines.append(f"  {idx}. {pattern}")
        if len(patterns) > 3:
            msg_lines.append(f"  ... 还有 {len(patterns) - 3} 条规则")
    else:
        global_pattern = Config.get_config("group_request_handler", "JOIN_REASON_PATTERN")
        msg_lines.append(f"\n【全局白名单规则】")
        msg_lines.append(f"  1. {global_pattern}")

    # 显示黑名单规则详情
    if blacklist:
        msg_lines.append("\n【黑名单规则列表】")
        for idx, item in enumerate(blacklist[:3], 1):
            pattern_str = item.get("pattern", "")
            reason_str = item.get("reason", "")
            msg_lines.append(f"  {idx}. {pattern_str}")
            msg_lines.append(f"     理由: {reason_str}")
        if len(blacklist) > 3:
            msg_lines.append(f"  ... 还有 {len(blacklist) - 3} 条规则")

    if notify_users:
        msg_lines.append("\n【提醒用户列表】")
        for idx, uid in enumerate(notify_users[:5], 1):
            msg_lines.append(f"  {idx}. {uid}")
        if len(notify_users) > 5:
            msg_lines.append(f"  ... 还有 {len(notify_users) - 5} 个")

    await MessageUtils.build_message("\n".join(msg_lines)).send()


# ==================== 私聊管理命令（超级用户） ====================

# 查看所有群列表
list_all_groups = on_alconna(
    Alconna("加群白名单列表"),
    priority=5,
    block=True,
)


@list_all_groups.handle()
async def _(bot: Bot, session: Uninfo):
    """查看所有群的白名单状态"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    whitelist = await data_manager.get_whitelist()

    if not whitelist:
        await MessageUtils.build_message(
            "当前白名单为空\n将处理所有群的加群申请"
        ).send()
        return

    msg_lines = ["【加群白名单列表】"]
    for idx, group_id in enumerate(sorted(whitelist), 1):
        notify_users = await data_manager.get_notify_users(group_id)
        patterns = await data_manager.get_pattern(group_id)
        status = f"提醒用户:{len(notify_users)}人"
        if patterns:
            status += f" 规则:{len(patterns)}条"
        msg_lines.append(f"{idx}. {group_id} ({status})")

    msg_lines.append(f"\n共 {len(whitelist)} 个群")

    await MessageUtils.build_message("\n".join(msg_lines)).send()


# 私聊添加白名单
pm_add_whitelist = on_alconna(
    Alconna("添加加群白名单", Args["group_id", str]),
    priority=5,
    block=True,
)


@pm_add_whitelist.handle()
async def _(bot: Bot, session: Uninfo, arparma: Arparma, group_id: Match[str]):
    """私聊添加白名单"""
    # 只允许超级用户在私聊中使用
    if session.group:
        # 如果在群里，调用原来的处理函数
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available:
        await MessageUtils.build_message("请提供群号\n示例: 添加加群白名单 123456789").send()
        return

    gid = group_id.result
    success = await data_manager.add_to_whitelist(gid)

    if success:
        logger.info(f"超级用户在私聊中添加群 {gid} 到白名单", "加群申请处理")
        await MessageUtils.build_message(f"✅ 已将群 {gid} 添加到白名单").send()
    else:
        await MessageUtils.build_message(f"❌ 群 {gid} 已在白名单中").send()


# 私聊移除白名单
pm_remove_whitelist = on_alconna(
    Alconna("移除加群白名单", Args["group_id", str]),
    priority=5,
    block=True,
)


@pm_remove_whitelist.handle()
async def _(bot: Bot, session: Uninfo, arparma: Arparma, group_id: Match[str]):
    """私聊移除白名单"""
    # 只允许超级用户在私聊中使用
    if session.group:
        # 如果在群里，调用原来的处理函数
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available:
        await MessageUtils.build_message("请提供群号\n示例: 移除加群白名单 123456789").send()
        return

    gid = group_id.result
    success = await data_manager.remove_from_whitelist(gid)

    if success:
        logger.info(f"超级用户在私聊中移除群 {gid} 的白名单", "加群申请处理")
        await MessageUtils.build_message(f"✅ 已将群 {gid} 从白名单移除").send()
    else:
        await MessageUtils.build_message(f"❌ 群 {gid} 不在白名单中").send()


# 私聊查看群状态
pm_show_status = on_alconna(
    Alconna("查看加群状态", Args["group_id", str]),
    priority=5,
    block=True,
)


@pm_show_status.handle()
async def _(bot: Bot, session: Uninfo, arparma: Arparma, group_id: Match[str]):
    """私聊查看群状态"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available:
        await MessageUtils.build_message("请提供群号\n示例: 查看加群状态 123456789").send()
        return

    gid = group_id.result

    # 获取配置
    enabled = Config.get_config("group_request_handler", "ENABLED")
    global_min_level = Config.get_config("group_request_handler", "MIN_QQ_LEVEL")
    auto_approve = Config.get_config("group_request_handler", "AUTO_APPROVE")

    # 获取群数据
    is_in_whitelist = await data_manager.is_in_whitelist(gid)
    notify_users = await data_manager.get_notify_users(gid)
    patterns = await data_manager.get_pattern(gid)
    min_level = await data_manager.get_min_level(gid)

    # 确定最低等级显示
    if min_level is not None:
        min_level_display = f"{min_level} (专属配置)"
    else:
        min_level_display = f"{global_min_level} (全局配置)"

    if patterns:
        pattern_display = f"{len(patterns)} 条专属规则"
        pattern_type = "(专属规则)"
    else:
        pattern_display = "1 条全局规则"
        pattern_type = "(全局规则)"

    msg_lines = [
        f"【群 {gid} 加群申请处理状态】",
        f"全局启用: {'✅ 是' if enabled else '❌ 否'}",
        f"白名单状态: {'✅ 在白名单' if is_in_whitelist else '❌ 不在白名单'}",
        f"最低QQ等级: {min_level_display}",
        f"自动同意: {'✅ 是' if auto_approve else '❌ 否(提醒管理员)'}",
        f"提醒用户数: {len(notify_users)}",
        f"加群理由规则: {pattern_display} {pattern_type}",
    ]

    # 显示规则详情
    if patterns:
        msg_lines.append("\n规则列表:")
        for idx, pattern in enumerate(patterns[:5], 1):
            msg_lines.append(f"  {idx}. {pattern}")
        if len(patterns) > 5:
            msg_lines.append(f"  ... 还有 {len(patterns) - 5} 条规则")
    else:
        global_pattern = Config.get_config("group_request_handler", "JOIN_REASON_PATTERN")
        msg_lines.append(f"\n全局规则:")
        msg_lines.append(f"  1. {global_pattern}")

    if notify_users:
        msg_lines.append("\n提醒用户列表:")
        for idx, uid in enumerate(notify_users[:10], 1):
            msg_lines.append(f"  {idx}. {uid}")
        if len(notify_users) > 10:
            msg_lines.append(f"  ... 还有 {len(notify_users) - 10} 个")

    await MessageUtils.build_message("\n".join(msg_lines)).send()


# 私聊设置提醒用户
pm_set_notify_users = on_alconna(
    Alconna("设置加群提醒", Args["group_id", str]["user_ids", str]),
    priority=5,
    block=True,
)


@pm_set_notify_users.handle()
async def _(
    bot: Bot,
    session: Uninfo,
    arparma: Arparma,
    group_id: Match[str],
    user_ids: Match[str],
):
    """私聊设置提醒用户"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available or not user_ids.available:
        await MessageUtils.build_message(
            "请提供群号和QQ号列表\n示例: 设置加群提醒 123456789 111111,222222,333333"
        ).send()
        return

    gid = group_id.result
    uids = [uid.strip() for uid in user_ids.result.split(",")]

    await data_manager.set_notify_users(gid, uids)

    logger.info(
        f"超级用户在私聊中设置群 {gid} 的提醒用户: {uids}", "加群申请处理"
    )
    await MessageUtils.build_message(
        f"✅ 已为群 {gid} 设置提醒用户\n共 {len(uids)} 人: {', '.join(uids)}"
    ).send()


# 私聊设置最低等级
pm_set_min_level = on_alconna(
    Alconna("设置最低等级", Args["group_id", str]["level", int]),
    priority=5,
    block=True,
)


@pm_set_min_level.handle()
async def _(
    bot: Bot,
    session: Uninfo,
    arparma: Arparma,
    group_id: Match[str],
    level: Match[int],
):
    """私聊设置最低等级"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available or not level.available:
        await MessageUtils.build_message(
            "请提供群号和等级\n示例: 设置最低等级 123456789 20"
        ).send()
        return

    gid = group_id.result
    min_level = level.result

    if min_level < 0:
        await MessageUtils.build_message("❌ 等级必须大于等于0").send()
        return

    await data_manager.set_min_level(gid, min_level)

    logger.info(
        f"超级用户在私聊中设置群 {gid} 的最低QQ等级: {min_level}",
        "加群申请处理",
    )
    await MessageUtils.build_message(
        f"✅ 已为群 {gid} 设置最低QQ等级: {min_level}"
    ).send()


# 私聊移除最低等级配置
pm_remove_min_level = on_alconna(
    Alconna("移除最低等级", Args["group_id", str]),
    priority=5,
    block=True,
)


@pm_remove_min_level.handle()
async def _(bot: Bot, session: Uninfo, arparma: Arparma, group_id: Match[str]):
    """私聊移除最低等级配置"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available:
        await MessageUtils.build_message("请提供群号\n示例: 移除最低等级 123456789").send()
        return

    gid = group_id.result
    success = await data_manager.remove_min_level(gid)

    if success:
        global_level = Config.get_config("group_request_handler", "MIN_QQ_LEVEL")
        logger.info(
            f"超级用户在私聊中移除群 {gid} 的最低等级配置", "加群申请处理"
        )
        await MessageUtils.build_message(
            f"✅ 已移除群 {gid} 的最低等级配置\n将使用全局配置: {global_level}"
        ).send()
    else:
        await MessageUtils.build_message(f"❌ 群 {gid} 未设置专属等级配置").send()


# 私聊添加群专属规则
pm_add_pattern = on_alconna(
    Alconna("添加加群规则", Args["group_id", str]["pattern", str]),
    priority=5,
    block=True,
)


@pm_add_pattern.handle()
async def _(
    bot: Bot,
    session: Uninfo,
    arparma: Arparma,
    group_id: Match[str],
    pattern: Match[str],
):
    """私聊添加群专属规则"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available or not pattern.available:
        await MessageUtils.build_message(
            "请提供群号和正则表达式\n示例: 添加加群规则 123456789 ^邀请码:[A-Z0-9]{6}$"
        ).send()
        return

    gid = group_id.result
    pattern_str = pattern.result

    # 验证正则表达式
    try:
        re.compile(pattern_str)
    except re.error as e:
        await MessageUtils.build_message(f"❌ 无效的正则表达式: {e}").send()
        return

    success = await data_manager.add_pattern(gid, pattern_str)

    if success:
        logger.info(
            f"超级用户在私聊中为群 {gid} 添加加群理由规则: {pattern_str}",
            "加群申请处理",
        )
        await MessageUtils.build_message(
            f"✅ 已为群 {gid} 添加加群理由规则:\n{pattern_str}"
        ).send()
    else:
        await MessageUtils.build_message("❌ 该规则已存在").send()


# 私聊删除群专属规则
pm_del_pattern = on_alconna(
    Alconna("删除加群规则", Args["group_id", str]["index", int]),
    priority=5,
    block=True,
)


@pm_del_pattern.handle()
async def _(
    bot: Bot,
    session: Uninfo,
    arparma: Arparma,
    group_id: Match[str],
    index: Match[int],
):
    """私聊删除群专属规则"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available or not index.available:
        await MessageUtils.build_message(
            "请提供群号和索引\n示例: 删除加群规则 123456789 1"
        ).send()
        return

    gid = group_id.result
    index_num = index.result

    success = await data_manager.remove_pattern_by_index(gid, index_num)

    if success:
        logger.info(
            f"超级用户在私聊中删除群 {gid} 的加群理由规则索引: {index_num}",
            "加群申请处理",
        )
        await MessageUtils.build_message(
            f"✅ 已删除群 {gid} 的规则 #{index_num}"
        ).send()
    else:
        await MessageUtils.build_message("❌ 删除失败，索引不存在").send()


# 私聊清空群专属规则
pm_clear_patterns = on_alconna(
    Alconna("清空加群规则", Args["group_id", str]),
    priority=5,
    block=True,
)


@pm_clear_patterns.handle()
async def _(bot: Bot, session: Uninfo, arparma: Arparma, group_id: Match[str]):
    """私聊清空群专属规则"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available:
        await MessageUtils.build_message("请提供群号\n示例: 清空加群规则 123456789").send()
        return

    gid = group_id.result
    success = await data_manager.clear_patterns(gid)

    if success:
        logger.info(
            f"超级用户在私聊中清空群 {gid} 的专属规则", "加群申请处理"
        )
        await MessageUtils.build_message(
            f"✅ 已清空群 {gid} 的所有专属规则\n将使用全局默认规则"
        ).send()
    else:
        await MessageUtils.build_message(f"❌ 群 {gid} 未设置专属规则").send()


# ==================== 私聊黑名单管理命令 ====================

# 私聊添加黑名单规则
pm_add_blacklist = on_alconna(
    Alconna("添加加群黑名单", Args["group_id", str]["pattern", str]["reason", str]),
    priority=5,
    block=True,
)


@pm_add_blacklist.handle()
async def _(
    bot: Bot, session: Uninfo, group_id: Match[str], pattern: Match[str], reason: Match[str]
):
    """私聊添加黑名单规则"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available or not pattern.available or not reason.available:
        await MessageUtils.build_message(
            "请提供群号、正则表达式和拒绝理由\n示例: 添加加群黑名单 123456789 .*垃圾.* 加群理由包含不当内容"
        ).send()
        return

    gid = group_id.result
    pattern_str = pattern.result.strip()
    reason_str = reason.result.strip()

    # 验证正则表达式
    try:
        re.compile(pattern_str)
    except re.error as e:
        await MessageUtils.build_message(f"❌ 正则表达式无效: {e}").send()
        return

    success = await data_manager.add_blacklist_pattern(gid, pattern_str, reason_str)

    if success:
        logger.info(
            f"超级用户在私聊中添加群 {gid} 的黑名单规则: {pattern_str} -> {reason_str}",
            "加群申请处理",
        )
        await MessageUtils.build_message(
            f"✅ 已添加群 {gid} 的黑名单规则\n正则: {pattern_str}\n拒绝理由: {reason_str}"
        ).send()
    else:
        await MessageUtils.build_message("❌ 该规则已存在").send()


# 私聊删除黑名单规则
pm_remove_blacklist = on_alconna(
    Alconna("删除加群黑名单", Args["group_id", str]["index", int]),
    priority=5,
    block=True,
)


@pm_remove_blacklist.handle()
async def _(bot: Bot, session: Uninfo, group_id: Match[str], index: Match[int]):
    """私聊删除黑名单规则"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available or not index.available:
        await MessageUtils.build_message(
            "请提供群号和索引\n示例: 删除加群黑名单 123456789 1"
        ).send()
        return

    gid = group_id.result
    idx = index.result

    success = await data_manager.remove_blacklist_by_index(gid, idx)

    if success:
        logger.info(
            f"超级用户在私聊中删除群 {gid} 的黑名单规则 #{idx}", "加群申请处理"
        )
        await MessageUtils.build_message(f"✅ 已删除群 {gid} 的黑名单规则 #{idx}").send()
    else:
        await MessageUtils.build_message("❌ 规则索引不存在").send()


# 私聊清空黑名单规则
pm_clear_blacklist = on_alconna(
    Alconna("清空加群黑名单", Args["group_id", str]),
    priority=5,
    block=True,
)


@pm_clear_blacklist.handle()
async def _(bot: Bot, session: Uninfo, group_id: Match[str]):
    """私聊清空黑名单规则"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available:
        await MessageUtils.build_message("请提供群号\n示例: 清空加群黑名单 123456789").send()
        return

    gid = group_id.result
    success = await data_manager.clear_blacklist(gid)

    if success:
        logger.info(f"超级用户在私聊中清空群 {gid} 的黑名单", "加群申请处理")
        await MessageUtils.build_message(f"✅ 已清空群 {gid} 的所有黑名单规则").send()
    else:
        await MessageUtils.build_message(f"❌ 群 {gid} 未设置黑名单规则").send()


# ==================== 私聊统计查询命令 ====================

# 私聊查看统计
pm_view_statistics = on_alconna(
    Alconna("查看加群统计", Args["group_id?", str]),
    priority=5,
    block=True,
)


@pm_view_statistics.handle()
async def _(bot: Bot, session: Uninfo, group_id: Match[str]):
    """私聊查看统计"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    # 如果指定了群号,查看该群统计
    if group_id.available:
        gid = group_id.result
        stats = await data_manager.get_statistics(gid)
        approved = stats.get("approved", 0)
        rejected = stats.get("rejected", 0)
        ai_approved = stats.get("ai_approved", 0)
        ai_rejected = stats.get("ai_rejected", 0)
        total = approved + rejected

        logs = await data_manager.get_request_logs(gid, limit=10)

        msg_lines = [
            f"【群 {gid} 加群申请统计】",
            f"总处理: {total} 次",
            f"✅ 已同意: {approved} 次",
            f"❌ 已拒绝: {rejected} 次",
        ]

        # 显示AI统计 - AI只能拒绝
        if ai_rejected > 0:
            ai_rate = (ai_rejected / total * 100) if total > 0 else 0
            msg_lines.append(f"\n🤖 AI拒绝: {ai_rejected} 次 ({ai_rate:.1f}%)")

        if total > 0:
            approve_rate = (approved / total) * 100
            msg_lines.append(f"\n总通过率: {approve_rate:.1f}%")

        if logs:
            msg_lines.append(f"\n【最近 {len(logs)} 条记录】")
            for log in logs:
                action_emoji = "✅" if log["action"] == "approve" else "❌"
                ai_badge = "🤖" if log.get("is_ai_reviewed") else ""
                timestamp = log["timestamp"][:19]
                msg_lines.append(
                    f"{action_emoji}{ai_badge} {timestamp} | {log['nickname']}({log['user_id']}) | 等级{log['level']}"
                )
                if log.get("reason"):
                    msg_lines.append(f"   理由: {log['reason']}")

    else:
        # 查看所有群的统计汇总
        all_stats = await data_manager.get_all_statistics()

        if not all_stats:
            await MessageUtils.build_message("❌ 暂无统计数据").send()
            return

        msg_lines = ["【所有群加群申请统计汇总】"]
        total_approved = 0
        total_rejected = 0
        total_ai_rejected = 0

        for gid, stats in all_stats.items():
            approved = stats.get("approved", 0)
            rejected = stats.get("rejected", 0)
            ai_rejected = stats.get("ai_rejected", 0)
            total = approved + rejected
            total_approved += approved
            total_rejected += rejected
            total_ai_rejected += ai_rejected

            if total > 0:
                approve_rate = (approved / total) * 100
                ai_info = f" | 🤖 {ai_rejected}" if ai_rejected > 0 else ""
                msg_lines.append(
                    f"\n群 {gid}:"
                    f"\n  总处理: {total} 次 | ✅ {approved} | ❌ {rejected}{ai_info} | 通过率: {approve_rate:.1f}%"
                )

        grand_total = total_approved + total_rejected
        if grand_total > 0:
            grand_approve_rate = (total_approved / grand_total) * 100
            grand_ai_rate = (total_ai_rejected / grand_total * 100) if grand_total > 0 else 0
            ai_summary = f" | 🤖 AI拒绝: {total_ai_rejected} ({grand_ai_rate:.1f}%)" if total_ai_rejected > 0 else ""
            msg_lines.insert(
                1,
                f"\n【总计】\n  总处理: {grand_total} 次 | ✅ {total_approved} | ❌ {total_rejected}{ai_summary} | 通过率: {grand_approve_rate:.1f}%\n"
            )

        msg_lines.append(
            "\n提示: 使用 '查看加群统计 [群号]' 查看指定群的详细日志"
        )

    await MessageUtils.build_message("\n".join(msg_lines)).send()


# 私聊查看日志
pm_view_logs = on_alconna(
    Alconna("查看加群日志", Args["group_id", str]["limit?", int]),
    priority=5,
    block=True,
)


@pm_view_logs.handle()
async def _(bot: Bot, session: Uninfo, group_id: Match[str], limit: Match[int]):
    """私聊查看日志"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not group_id.available:
        await MessageUtils.build_message(
            "请提供群号\n示例: 查看加群日志 123456789 20"
        ).send()
        return

    gid = group_id.result
    log_limit = limit.result if limit.available else 10

    logs = await data_manager.get_request_logs(gid, limit=log_limit)

    if not logs:
        await MessageUtils.build_message(f"❌ 群 {gid} 暂无申请日志").send()
        return

    msg_lines = [f"【群 {gid} 加群申请日志】(最近 {len(logs)} 条)"]

    for log in logs:
        action_emoji = "✅" if log["action"] == "approve" else "❌"
        timestamp = log["timestamp"][:19]
        msg_lines.append(
            f"\n{action_emoji} {timestamp}"
            f"\n  用户: {log['nickname']}({log['user_id']})"
            f"\n  等级: {log['level']}"
            f"\n  理由: {log['comment'][:50]}{'...' if len(log['comment']) > 50 else ''}"
        )
        if log.get("reason"):
            msg_lines.append(f"  拒绝理由: {log['reason']}")

    await MessageUtils.build_message("\n".join(msg_lines)).send()


# 私聊查询用户申请
pm_query_user_request = on_alconna(
    Alconna("查询用户申请", Args["user_id", str]["group_id", str]),
    priority=5,
    block=True,
)


@pm_query_user_request.handle()
async def _(bot: Bot, session: Uninfo, user_id: Match[str], group_id: Match[str]):
    """私聊查询用户的通过记录"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    if not user_id.available or not group_id.available:
        await MessageUtils.build_message(
            "请提供用户QQ号和群号\n示例: 查询用户申请 123456 789012345"
        ).send()
        return

    uid = user_id.result
    gid = group_id.result

    # 查询通过记录
    record = await data_manager.get_user_approved_request(uid, gid)

    if not record:
        await MessageUtils.build_message(
            f"❌ 未找到用户 {uid} 在群 {gid} 的通过记录"
        ).send()
        return

    # 格式化时间
    timestamp = record.get("timestamp", "")[:19].replace("T", " ")

    # 判断审核方式
    if record.get("is_ai_reviewed"):
        review_method = "AI自动审核"
    else:
        review_method = "人工/自动审核"

    # 构建返回消息
    msg_lines = [
        f"【用户 {uid} 在群 {gid} 的通过记录】",
        f"\n申请人昵称: {record.get('nickname', '未知')}",
        f"申请人QQ: {record.get('user_id', '未知')}",
        f"QQ等级: {record.get('level', 0)}",
        f"\n通过时间: {timestamp}",
        f"审核方式: {review_method}",
        f"\n加群理由:",
        f"{record.get('comment', '无')}",
    ]

    await MessageUtils.build_message("\n".join(msg_lines)).send()


# 私聊帮助命令
pm_help = on_alconna(
    Alconna("加群管理帮助"),
    priority=5,
    block=True,
)


@pm_help.handle()
async def _(bot: Bot, session: Uninfo):
    """私聊帮助"""
    # 只允许超级用户在私聊中使用
    if session.group:
        await MessageUtils.build_message("该命令仅支持私聊使用").send()
        return

    if session.user.id not in bot.config.superusers:
        await MessageUtils.build_message("❌ 该命令仅超级用户可用").send()
        return

    help_text = """【加群申请处理 - 私聊管理命令】

查询命令:
  加群白名单列表
    - 查看所有群的白名单状态

  查看加群状态 [群号]
    - 查看指定群的详细配置
    示例: 查看加群状态 123456789

  查看加群统计 [群号?]
    - 查看统计数据(不指定群号则查看所有群汇总)
    示例: 查看加群统计
    示例: 查看加群统计 123456789

  查看加群日志 [群号] [数量?]
    - 查看指定群的详细日志(默认10条)
    示例: 查看加群日志 123456789 20

  查询用户申请 [QQ号] [群号]
    - 查询指定用户在指定群的通过记录
    示例: 查询用户申请 123456 789012345

白名单管理:
  添加加群白名单 [群号]
    - 将指定群添加到白名单
    示例: 添加加群白名单 123456789

  移除加群白名单 [群号]
    - 将指定群从白名单移除
    示例: 移除加群白名单 123456789

提醒用户管理:
  设置加群提醒 [群号] [QQ号列表]
    - 设置群的提醒用户(用逗号分隔)
    示例: 设置加群提醒 123456789 111111,222222

等级管理:
  设置最低等级 [群号] [等级]
    - 设置群的最低QQ等级要求
    示例: 设置最低等级 123456789 20

  移除最低等级 [群号]
    - 移除群的专属等级要求,使用全局配置
    示例: 移除最低等级 123456789

白名单规则管理:
  添加加群规则 [群号] [正则表达式]
    - 添加群的白名单规则(符合则通过)
    示例: 添加加群规则 123456789 ^邀请码:[A-Z0-9]{6}$

  删除加群规则 [群号] [索引]
    - 删除群的指定规则
    示例: 删除加群规则 123456789 1

  清空加群规则 [群号]
    - 清空群的所有白名单规则,使用全局规则
    示例: 清空加群规则 123456789

黑名单规则管理:
  添加加群黑名单 [群号] [正则] [理由]
    - 添加黑名单规则(符合则自动拒绝)
    示例: 添加加群黑名单 123456789 .*垃圾.* 加群理由包含不当内容

  删除加群黑名单 [群号] [索引]
    - 删除群的指定黑名单规则
    示例: 删除加群黑名单 123456789 1

  清空加群黑名单 [群号]
    - 清空群的所有黑名单规则
    示例: 清空加群黑名单 123456789

注意:
  - 所有命令仅超级用户可在私聊中使用
  - 全局配置请通过 Web UI 修改
  - 群内命令请在对应群聊中使用
  - 黑名单优先级高于白名单,匹配黑名单将直接拒绝"""

    await MessageUtils.build_message(help_text).send()


# ==================== 私聊回复处理 ====================

# 监听私聊消息回复
reply_handler = on_message(priority=10, block=False)


@reply_handler.handle()
async def _(bot: Bot, event: MessageEvent):
    """处理对通知消息的回复"""
    # 只处理私聊消息
    if not isinstance(event, PrivateMessageEvent):
        return

    # 检查消息是否是回复
    reply = event.reply
    if not reply:
        return

    # 获取被回复的消息ID
    reply_message_id = str(reply.message_id)

    # 检查是否是待处理的申请
    request_info = await data_manager.get_pending_request(reply_message_id)
    if not request_info:
        return

    # 清理过期的申请记录
    await data_manager.clean_expired_requests()

    # 获取用户输入的内容
    message_text = event.get_plaintext().strip()

    # 解析用户的回复
    if message_text.startswith("同意"):
        # 同意申请
        try:
            await bot.set_group_add_request(
                flag=request_info["flag"],
                sub_type="add",
                approve=True
            )

            # 记录统计和日志
            group_id_str = str(request_info['group_id'])
            user_id_req = request_info['user_id']
            await data_manager.increment_approved(group_id_str)

            # 获取QQ等级用于日志
            try:
                user_info = await bot.get_stranger_info(user_id=user_id_req)
                qq_level = user_info.get("level", 0)
            except Exception:
                qq_level = 0

            await data_manager.add_request_log(
                group_id=group_id_str,
                user_id=user_id_req,
                nickname=request_info['nickname'],
                comment=request_info['comment'],
                action="approve",
                level=qq_level
            )

            await bot.send_private_msg(
                user_id=event.user_id,
                message=f"✅ 已同意用户 {request_info['nickname']}({request_info['user_id']}) 加入群 {request_info['group_id']}"
            )

            logger.info(
                f"用户 {event.user_id} 通过回复同意了加群申请: {request_info['nickname']}({request_info['user_id']}) -> 群 {request_info['group_id']}",
                "加群申请处理",
                target=request_info['group_id']
            )

            # 移除已处理的申请
            await data_manager.remove_pending_request(reply_message_id)

        except Exception as e:
            logger.error(
                f"同意加群申请失败: {e}",
                "加群申请处理",
                e=e
            )
            await bot.send_private_msg(
                user_id=event.user_id,
                message=f"❌ 处理失败: {e}\n可能该申请已过期或已被处理"
            )

    elif message_text.startswith("拒绝"):
        # 拒绝申请,可选理由
        parts = message_text.split(maxsplit=1)
        reason = parts[1] if len(parts) > 1 else "管理员已拒绝"

        try:
            await bot.set_group_add_request(
                flag=request_info["flag"],
                sub_type="add",
                approve=False,
                reason=reason
            )

            # 记录统计和日志
            group_id_str = str(request_info['group_id'])
            user_id_req = request_info['user_id']
            await data_manager.increment_rejected(group_id_str)

            # 获取QQ等级用于日志
            try:
                user_info = await bot.get_stranger_info(user_id=user_id_req)
                qq_level = user_info.get("level", 0)
            except Exception:
                qq_level = 0

            await data_manager.add_request_log(
                group_id=group_id_str,
                user_id=user_id_req,
                nickname=request_info['nickname'],
                comment=request_info['comment'],
                action="reject",
                level=qq_level,
                reason=reason
            )

            await bot.send_private_msg(
                user_id=event.user_id,
                message=f"✅ 已拒绝用户 {request_info['nickname']}({request_info['user_id']}) 加入群 {request_info['group_id']}\n拒绝理由: {reason}"
            )

            logger.info(
                f"用户 {event.user_id} 通过回复拒绝了加群申请: {request_info['nickname']}({request_info['user_id']}) -> 群 {request_info['group_id']}, 理由: {reason}",
                "加群申请处理",
                target=request_info['group_id']
            )

            # 移除已处理的申请
            await data_manager.remove_pending_request(reply_message_id)

        except Exception as e:
            logger.error(
                f"拒绝加群申请失败: {e}",
                "加群申请处理",
                e=e
            )
            await bot.send_private_msg(
                user_id=event.user_id,
                message=f"❌ 处理失败: {e}\n可能该申请已过期或已被处理"
            )
    else:
        # 未识别的指令,不处理
        return


# ==================== AI自动审核定时任务 ====================

@scheduler.scheduled_job("interval", seconds=30, id="check_timeout_requests")
async def check_timeout_requests():
    """定时检查超时的加群申请并使用AI自动审核"""
    try:
        # 检查功能是否启用
        ai_enabled = Config.get_config("group_request_handler", "AI_AUTO_REVIEW_ENABLED")
        if not ai_enabled:
            return

        # 获取配置
        timeout_seconds = Config.get_config("group_request_handler", "AI_REVIEW_TIMEOUT") or 180
        min_confidence = Config.get_config("group_request_handler", "AI_MIN_CONFIDENCE") or 0.7
        ai_model = Config.get_config("group_request_handler", "AI_REVIEW_MODEL")

        # 获取超时的请求
        timeout_list = await data_manager.get_timeout_requests(timeout_seconds)

        if not timeout_list:
            return

        logger.info(
            f"发现 {len(timeout_list)} 个超时未处理的加群申请，开始AI自动审核",
            "加群申请处理"
        )

        # 获取bot实例
        from nonebot import get_bots
        bots = get_bots()
        if not bots:
            logger.warning("没有可用的bot实例，无法处理超时请求", "加群申请处理")
            return

        # 使用第一个可用的bot
        bot = list(bots.values())[0]

        # 处理每个超时的请求
        for message_id, request_info in timeout_list:
            try:
                user_id = request_info['user_id']
                group_id = request_info['group_id']
                flag = request_info['flag']
                nickname = request_info['nickname']
                comment = request_info['comment']
                qq_level = request_info.get('qq_level', 0)

                logger.info(
                    f"开始AI审核超时申请: {nickname}({user_id}) -> 群 {group_id}",
                    "加群申请处理",
                    target=group_id
                )

                # 使用AI分析
                review_result = await analyze_join_request(
                    user_id=user_id,
                    nickname=nickname,
                    qq_level=qq_level,
                    comment=comment,
                    group_id=group_id,
                    model_name=ai_model
                )

                # 检查置信度
                if review_result.confidence < min_confidence:
                    logger.warning(
                        f"AI审核置信度({review_result.confidence:.2f})低于阈值({min_confidence})，跳过自动处理",
                        "加群申请处理",
                        target=group_id
                    )
                    # 不移除请求，继续等待人工处理
                    continue

                # 根据AI判断结果处理申请
                group_id_str = str(group_id)

                # AI只负责拒绝，不处理通过的情况
                if not review_result.should_approve:
                    # AI建议拒绝 - 直接执行拒绝
                    try:
                        # 使用AI生成的精准拒绝理由
                        reject_reason = review_result.reject_message
                        await bot.set_group_add_request(
                            flag=flag,
                            sub_type="add",
                            approve=False,
                            reason=reject_reason
                        )

                        # 记录统计和日志
                        await data_manager.increment_rejected(group_id_str)
                        await data_manager.increment_ai_rejected(group_id_str)
                        await data_manager.add_request_log(
                            group_id=group_id_str,
                            user_id=user_id,
                            nickname=nickname,
                            comment=comment,
                            action="reject",
                            level=qq_level,
                            reason=f"AI自动拒绝(置信度:{review_result.confidence:.2f})",
                            is_ai_reviewed=True
                        )

                        logger.info(
                            f"AI自动拒绝: {nickname}({user_id}) -> 群 {group_id}, "
                            f"置信度:{review_result.confidence:.2f}, 理由:{review_result.reason}, "
                            f"拒绝消息:{reject_reason}",
                            "加群申请处理",
                            target=group_id
                        )

                        # 通知管理员
                        notify_users = await data_manager.get_notify_users(group_id_str)
                        if notify_users:
                            notification = (
                                f"【AI自动拒绝】\n"
                                f"群号: {group_id}\n"
                                f"申请人: {nickname}({user_id})\n"
                                f"QQ等级: {qq_level}\n"
                                f"加群理由: {comment}\n"
                                f"拒绝理由: {reject_reason}\n"
                                f"置信度: {review_result.confidence:.2%}\n"
                                f"风险等级: {review_result.risk_level}\n"
                                f"AI分析: {review_result.reason}"
                            )
                            for uid in notify_users:
                                try:
                                    await bot.send_private_msg(
                                        user_id=int(uid),
                                        message=notification
                                    )
                                except Exception as e:
                                    logger.error(f"通知用户 {uid} 失败: {e}", "加群申请处理")

                        # 移除已处理的请求
                        await data_manager.remove_pending_request(message_id)

                    except Exception as e:
                        from nonebot.adapters.onebot.v11 import ActionFailed
                        # 只要是ActionFailed就说明请求已无法处理,直接移除
                        if isinstance(e, ActionFailed):
                            error_msg = getattr(e, 'message', None) or getattr(e, 'wording', str(e))
                            logger.warning(
                                f"AI拒绝申请失败(请求已失效): {nickname}({user_id}) -> 群 {group_id}, 错误:{error_msg}, 移除记录",
                                "加群申请处理",
                                target=group_id
                            )
                            # 移除pending记录
                            await data_manager.remove_pending_request(message_id)
                        else:
                            logger.error(
                                f"AI自动拒绝申请失败: {e}",
                                "加群申请处理",
                                target=group_id,
                                e=e
                            )
                        continue
                else:
                    # AI认为没问题 - 不处理，静默继续等待人工审核
                    logger.info(
                        f"AI审核未发现明显问题: {nickname}({user_id}) -> 群 {group_id}, "
                        f"置信度:{review_result.confidence:.2f}, 继续等待人工处理",
                        "加群申请处理",
                        target=group_id
                    )
                    # 不移除pending记录，不发送通知，继续

            except Exception as e:
                logger.error(
                    f"处理超时请求时出错: {e}",
                    "加群申请处理",
                    e=e
                )
                continue

    except Exception as e:
        logger.error(f"检查超时请求任务失败: {e}", "加群申请处理", e=e)
