"""WebSocket 路由"""

import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from nonebot import get_driver, on_message
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot_plugin_alconna import At, Hyper, Image, Text, UniMsg
from nonebot_plugin_uninfo import Uninfo
from starlette.websockets import WebSocketState

from zhenxun.models.group_member_info import GroupInfoUser
from zhenxun.services.log import logger
from zhenxun.utils.depends import UserName

from ..services.common import qq_avatar_url
from ..services.log_service import LOG_STORAGE

router = APIRouter()

ws_log_router = APIRouter(prefix="/logs", tags=["WebSocket 日志"])
ws_status_router = APIRouter(prefix="/status", tags=["WebSocket 状态"])
ws_chat_router = APIRouter(prefix="/chat", tags=["WebSocket 聊天"])


@ws_log_router.websocket("")
async def logs_realtime(websocket: WebSocket):
    """实时日志 WebSocket

    订阅系统日志实时推送。
    """
    await websocket.accept()
    queue = LOG_STORAGE.subscribe()

    try:
        # 只在连接时发送一次历史日志
        logs = LOG_STORAGE.get_logs(limit=50)
        for log in logs:
            await websocket.send_json(log)

        # 持续接收新日志
        while websocket.client_state == WebSocketState.CONNECTED:
            try:
                log_entry = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_json(log_entry)
            except asyncio.TimeoutError:
                # 发送心跳
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        logger.debug("日志 WebSocket 连接断开")
    except Exception as e:
        logger.error(f"日志 WebSocket 错误：{e!s}")
    finally:
        LOG_STORAGE.unsubscribe(queue)
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass


@ws_status_router.websocket("")
async def status_realtime(websocket: WebSocket):
    """实时状态 WebSocket

    推送系统状态信息。
    """
    from ..services.system_service import get_system_status

    await websocket.accept()

    try:
        while websocket.client_state == WebSocketState.CONNECTED:
            # 获取系统状态
            status = await get_system_status()
            await websocket.send_json(
                {
                    "type": "status",
                    "data": {
                        "cpu": status.cpu,
                        "memory": status.memory,
                        "disk": status.disk,
                        "check_time": status.check_time.isoformat(),
                    },
                }
            )

            # 等待一段时间
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.debug("状态 WebSocket 连接断开")
    except Exception as e:
        logger.error(f"状态 WebSocket 错误：{e!s}")
    finally:
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass


# 聊天 WebSocket 相关
_chat_connections: list[WebSocket] = []
_message_cache: dict = {}
MAX_CACHE_SIZE = 100

# 旧项目的聊天 WebSocket 兼容实现
_driver = get_driver()
_ws_chat_conn: WebSocket | None = None
_id2name: dict[str, dict[str, str]] = {}
_id_list: list = []

_chat_matcher = on_message(block=False, priority=1, rule=lambda: bool(_ws_chat_conn))


@_driver.on_shutdown
async def _():
    """关闭 WebSocket 连接"""
    if _ws_chat_conn and _ws_chat_conn.client_state == WebSocketState.CONNECTED:
        await _ws_chat_conn.close()


async def _message_handle(
    message: UniMsg,
    group_id: str | None,
):
    """消息处理"""
    time_str = str(datetime.now().replace(microsecond=0))
    messages = []
    for m in message:
        if isinstance(m, Text | str):
            messages.append({"type": "text", "msg": str(m), "time": time_str})
        elif isinstance(m, Image):
            if m.url:
                messages.append({"type": "img", "msg": m.url, "time": time_str})
        elif isinstance(m, At):
            if group_id:
                if m.target == "0":
                    uname = "全体成员"
                else:
                    uname = m.target
                    if group_id not in _id2name:
                        _id2name[group_id] = {}
                    if m.target in _id2name[group_id]:
                        uname = _id2name[group_id][m.target]
                    elif group_user := await GroupInfoUser.get_or_none(
                        user_id=m.target, group_id=group_id
                    ):
                        uname = group_user.user_name
                        if m.target not in _id2name[group_id]:
                            _id2name[group_id][m.target] = uname
                messages.append({"type": "at", "msg": f"@{uname}", "time": time_str})
        elif isinstance(m, Hyper):
            messages.append({"type": "text", "msg": "[分享消息]", "time": time_str})
    return messages


@_chat_matcher.handle()
async def _(
    message: UniMsg, event: MessageEvent, session: Uninfo, uname: str = UserName()
):
    """监听聊天消息并推送给 WebSocket 客户端"""
    global _ws_chat_conn, _id2name, _id_list

    if _ws_chat_conn and _ws_chat_conn.client_state == WebSocketState.CONNECTED:
        msg_id = event.message_id
        if msg_id in _id_list:
            return
        _id_list.append(msg_id)
        if len(_id_list) > 50:
            _id_list = _id_list[40:]

        # 过滤掉 Bot 自己发送的消息（避免重复显示）
        bot_id = session.self_id
        if bot_id and str(session.user.id) == str(bot_id):
            return

        gid = session.group.id if session.group else None
        messages = await _message_handle(message, gid)

        from zhenxun.configs.config import Config as gConfig

        ava_url = gConfig.get_config(
            "web-ui",
            "ava_url",
            qq_avatar_url(session.user.id, size=160),
        )

        data = {
            "object_id": gid or session.user.id,
            "user_id": session.user.id,
            "group_id": gid,
            "message": messages,
            "name": uname,
            "ava_url": (
                ava_url.format(session.user.id) if isinstance(ava_url, str) else ava_url
            ),
        }
        await _ws_chat_conn.send_json(data)


@ws_chat_router.websocket("")
async def chat_realtime(websocket: WebSocket):
    """实时聊天 WebSocket

    接收和推送聊天消息。
    """
    global _ws_chat_conn

    await websocket.accept()
    _ws_chat_conn = websocket
    _chat_connections.append(websocket)

    try:
        while websocket.client_state == WebSocketState.CONNECTED:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=0.5)
                # 处理发送消息（只发送到QQ，不广播回前端）
                await _handle_websocket_message(data)
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass
    except WebSocketDisconnect:
        logger.debug("聊天 WebSocket 连接断开")
    except Exception as e:
        logger.error(f"聊天 WebSocket 错误：{e!s}")
    finally:
        _ws_chat_conn = None
        if websocket in _chat_connections:
            _chat_connections.remove(websocket)
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass


async def _handle_send_message(data: dict) -> bool:
    """处理发送消息到 QQ

    参数:
        data: WebSocket 接收的消息数据，包含 self_id, group_id, user_id, message

    返回:
        bool: 是否发送成功
    """
    from ..services.manage_service import ManageService

    try:
        self_id = data.get("self_id")
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        message = data.get("message")

        if not message:
            logger.warning("WebSocket 消息发送失败：消息内容为空")
            return False

        # 调用 ManageService.send_message 发送消息
        result = await ManageService.send_message(
            bot_id=self_id,
            user_id=user_id,
            group_id=group_id,
            message=message,
        )
        return result
    except Exception as e:
        logger.error(f"WebSocket 消息发送失败：{e}", "WebSocket")
        return False


async def _handle_websocket_message(data: dict):
    """处理 WebSocket 接收的消息

    只发送到 QQ，不广播回 WebSocket（前端已经本地显示）
    """
    await _handle_send_message(data)
