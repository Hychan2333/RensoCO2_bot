"""系统服务"""

from datetime import datetime
import platform

import cpuinfo
from nonebot.utils import run_sync
import psutil

from zhenxun.configs.config import BotConfig
from zhenxun.models.group_console import GroupConsole
from zhenxun.utils._restart_utils import request_restart
from zhenxun.utils.http_utils import AsyncHttpx

from ..exceptions import SystemException
from ..models.system import BotStatus, SystemHealth, SystemStatus
from ..utils.formatters import format_uptime

BAIDU_URL = "https://www.baidu.com/"
GOOGLE_URL = "https://www.google.com/"
_cpu_percent_last = 0.0


def _get_status_level(value: float) -> tuple[str, str]:
    """获取状态级别"""
    if value > 90:
        return "critical", "error"
    if value > 70:
        return "high", "warning"
    return "normal", "healthy"


@run_sync
def get_system_status() -> SystemStatus:
    """获取系统状态"""
    global _cpu_percent_last
    cpu = psutil.cpu_percent(interval=0.5)
    if cpu == 0.0:
        cpu = _cpu_percent_last
    _cpu_percent_last = cpu

    return SystemStatus(
        cpu=cpu,
        memory=psutil.virtual_memory().percent,
        disk=psutil.disk_usage("/").percent,
        check_time=datetime.now().replace(microsecond=0),
    )


@run_sync
def get_system_health() -> SystemHealth:
    """获取系统健康状态"""
    cpu = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent

    cpu_status, cpu_health = _get_status_level(cpu)
    memory_status, memory_health = _get_status_level(memory)
    disk_status, disk_health = _get_status_level(disk)

    # 总体健康状态
    status = "healthy"
    if "error" in [cpu_health, memory_health, disk_health]:
        status = "error"
    elif "warning" in [cpu_health, memory_health, disk_health]:
        status = "warning"

    # 生成优化建议
    recommendations = []
    if cpu > 80:
        recommendations.append("CPU 使用率较高，建议检查高负载进程")
    if memory > 80:
        recommendations.append("内存使用率较高，建议检查内存占用")
    if disk > 80:
        recommendations.append("磁盘使用率较高，建议清理无用文件")

    return SystemHealth(
        status=status,
        cpu_status=cpu_status,
        memory_status=memory_status,
        disk_status=disk_status,
        recommendations=recommendations,
    )


async def get_bot_status() -> BotStatus:
    """获取 Bot 状态"""
    import nonebot

    bots = nonebot.get_bots()
    is_running = len(bots) > 0

    # 获取运行时长
    uptime = 0
    start_time = datetime.now()
    try:
        from zhenxun.models.bot_connect_log import BotConnectLog

        latest_connect = (
            await BotConnectLog.filter(type=1).order_by("-connect_time").first()
        )
        if latest_connect and latest_connect.connect_time:
            start_time = latest_connect.connect_time
            uptime = int((datetime.now() - start_time).total_seconds())
    except Exception:
        pass

    # 获取群组数量
    group_count = 0
    try:
        group_count = await GroupConsole.all().count()
    except Exception:
        pass

    return BotStatus(
        is_running=is_running,
        uptime=uptime,
        uptime_formatted=format_uptime(uptime),
        group_count=group_count,
        friend_count=0,
        message_count=0,
        start_time=start_time,
    )


async def check_network() -> dict[str, bool]:
    """检查网络连通性"""
    baidu, google = True, True
    try:
        await AsyncHttpx.get(BAIDU_URL, timeout=5)
    except Exception:
        baidu = False
    try:
        await AsyncHttpx.get(GOOGLE_URL, timeout=5)
    except Exception:
        google = False
    return {"baidu": baidu, "google": google}


@run_sync
def get_system_info() -> dict:
    """获取详细系统信息"""
    from pathlib import Path

    system = platform.uname()
    cpu_info = cpuinfo.get_cpu_info()
    cpu_freq = psutil.cpu_freq()

    # 读取版本信息
    version = "unknown"
    version_file = Path("__version__")
    if version_file.exists():
        try:
            content = version_file.read_text("utf-8").strip()
            version = content.split(":", 1)[1].strip() if ":" in content else content
        except Exception:
            pass

    return {
        "version": version,
        "system": f"{system.system} {system.release}",
        "arch": system.machine,
        "cpu_brand": cpu_info.get("brand_raw", "Unknown"),
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_freq_mhz": round(cpu_freq.current, 2) if cpu_freq else 0,
        "memory_total": round(psutil.virtual_memory().total / (1024**3), 2),
        "nickname": BotConfig.self_nickname,
    }


async def restart_bot() -> bool:
    """重启 Bot"""
    ok, message = await request_restart("webui.system")
    if not ok:
        raise SystemException(message)
    return True
