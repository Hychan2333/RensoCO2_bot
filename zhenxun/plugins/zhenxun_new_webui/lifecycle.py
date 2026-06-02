"""WebUI 后端启动注册逻辑。"""

import asyncio
from pathlib import Path
import re

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from nonebot.log import default_filter, default_format

from zhenxun.services.log import logger, logger_

from .exceptions import APIException
from .responses import error_response
from .services.log_service import LOG_STORAGE

ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
_LOG_TASKS: set[asyncio.Task] = set()


async def log_sink(message: str) -> None:
    """写入 WebUI 日志缓存。"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    clean_message = ANSI_ESCAPE_PATTERN.sub("", message.rstrip("\n"))
    task = loop.create_task(LOG_STORAGE.add(clean_message))
    _LOG_TASKS.add(task)
    task.add_done_callback(_LOG_TASKS.discard)


def register_log_sink() -> None:
    """注册日志监听。"""
    logger_.add(
        log_sink,
        colorize=True,
        filter=default_filter,
        format=default_format,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册 API 异常处理器。"""

    @app.exception_handler(APIException)
    async def api_exception_handler(request, exc: APIException):
        return JSONResponse(
            status_code=exc.code,
            content=error_response(
                message=exc.message,
                code=exc.code,
                data=exc.data,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        logger.error(f"Unexpected error: {exc!s}", "WebUiNext")
        return JSONResponse(
            status_code=500,
            content=error_response(
                message=f"服务器内部错误：{exc!s}",
                code=500,
            ).model_dump(),
        )


def mount_frontend(app: FastAPI) -> None:
    """挂载前端 dist。"""
    dist_path = Path(__file__).parent / "dist"
    if not dist_path.exists():
        logger.warning(f"dist目录不存在: {dist_path}", "WebUiNext")
        return

    app.mount(
        "/next",
        StaticFiles(directory=str(dist_path), html=True),
        name="webui-next",
    )
    logger.info("<g>WebUI Next 前端挂载成功: /next</g>", "WebUiNext")


def setup_webui(app: FastAPI, api_router, ws_router) -> None:
    """注册 WebUI 后端组件。"""
    register_log_sink()
    register_exception_handlers(app)
    app.include_router(api_router)
    app.include_router(ws_router)
    mount_frontend(app)
