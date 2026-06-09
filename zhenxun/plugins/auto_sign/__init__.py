from pathlib import Path

import nonebot
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import Target
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_uninfo import Scene, SceneType, Session, User

from zhenxun.configs.config import Config
from zhenxun.configs.utils import PluginExtraData, RegisterConfig
from zhenxun.models.sign_user import SignUser
from zhenxun.services.log import logger
from zhenxun.utils.message import MessageUtils

try:
    from zhenxun.builtin_plugins.sign_in._data_source import SignManage
except ImportError:
    logger.error("无法导入 SignManage，请检查签到插件是否存在", "自动签到")
    raise

__plugin_meta__ = PluginMetadata(
    name="自动签到",
    description="每天固定时间给指定用户列表自动签到并私聊发送卡片",
    usage="请在配置文件中配置 AUTO_SIGN_USER_IDS 和 AUTO_SIGN_TIME",
    extra=PluginExtraData(
        author="AIGC_Hychan2333",
        version="1.0",
        configs=[
            RegisterConfig(
                module="auto_sign",
                key="user_ids",
                value=[],
                type=list,
                help="需要自动签到的用户ID(QQ号)列表",
            ),
            RegisterConfig(
                module="auto_sign",
                key="hour",
                value=8,
                type=int,
                help="自动签到的小时 (0-23)",
            ),
            RegisterConfig(
                module="auto_sign",
                key="minute",
                value=0,
                type=int,
                help="自动签到的分钟 (0-59)",
            ),
        ],
    ).to_dict(),
)

auto_sign_config = Config.get("auto_sign")
USER_IDS = auto_sign_config.get("user_ids", [])
HOUR = auto_sign_config.get("hour", 8)
MINUTE = auto_sign_config.get("minute", 0)

logger.info("自动签到插件已加载", "自动签到")
logger.info(f"配置的用户列表: {USER_IDS}", "自动签到")
logger.info(f"设定时间: {HOUR}:{MINUTE}", "自动签到")


@scheduler.scheduled_job(
    "cron",
    hour=HOUR,
    minute=MINUTE,
    id="auto_sign_daily",
    max_instances=1,
    misfire_grace_time=60,
)
async def auto_sign_task():
    logger.info("=" * 50, "自动签到")
    logger.info(f"定时任务触发！当前配置用户数: {len(USER_IDS)}", "自动签到")

    if not USER_IDS:
        logger.warning("用户列表为空，跳过签到", "自动签到")
        return

    logger.info(f"开始执行自动签到任务，目标用户: {USER_IDS}", "自动签到")

    bots = nonebot.get_bots()
    logger.info(f"当前可用 Bot 数量: {len(bots)}", "自动签到")

    if not bots:
        logger.error("当前没有可用的 Bot，无法执行自动签到", "自动签到")
        return

    bot = list(bots.values())[0]
    logger.info(f"使用 Bot: {bot.self_id}", "自动签到")

    for user_id in USER_IDS:
        try:
            logger.info(f"正在处理用户: {user_id}", "自动签到")

            user, _ = await SignUser.get_or_create(
                user_id=user_id, defaults={"platform": "QQ"}
            )

            try:
                info = await bot.get_stranger_info(user_id=user_id)
                nickname = info.get("nickname", str(user_id))
                logger.info(f"用户 {user_id} 昵称: {nickname}", "自动签到")
            except Exception as e:
                logger.warning(
                    f"获取用户 {user_id} 信息失败: {e}，使用用户ID", "自动签到"
                )
                nickname = str(user_id)

            try:
                user_obj = User(id=str(user_id), name=nickname)
                scene_obj = Scene(id=str(user_id), type=SceneType.PRIVATE)

                session_obj = Session(
                    self_id=str(bot.self_id),
                    adapter="OneBot V11",
                    scope="QQClient",
                    scene=scene_obj,
                    user=user_obj,
                    member=None,
                    operator=None,
                    platform="QQ",
                )

                logger.info("调用签到接口...", "自动签到")
                path = await SignManage.sign(session_obj, nickname)

                if path and isinstance(path, Path) and path.exists():
                    try:
                        target = Target(user_id, private=True)
                        await MessageUtils.build_message(path).send(target, bot)
                        logger.info(
                            f"已向用户 {user_id}({nickname}) 发送签到卡片", "自动签到"
                        )
                    except Exception as e:
                        logger.error(f"发送私聊消息失败: {e}", "自动签到", e=e)
                else:
                    logger.warning(f"签到未生成有效卡片: {path}", "自动签到")

            except Exception as e:
                logger.error(f"签到过程出错: {e}", "自动签到", e=e)

        except Exception as e:
            logger.error(f"用户 {user_id} 签到失败: {e}", "自动签到", e=e)

    logger.info("自动签到任务执行完毕", "自动签到")
    logger.info("=" * 50, "自动签到")
