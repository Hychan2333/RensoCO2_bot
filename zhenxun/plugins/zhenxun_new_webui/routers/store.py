"""插件商店路由"""

from pydantic import BaseModel

from ..dependencies import AuthenticatedUser
from ..exceptions import APIException
from ..responses import APIResponse, success_response
from ..routing import WebUIRouter

router = WebUIRouter(prefix="/store", tags=["插件商店"])


class StorePluginInfo(BaseModel):
    """插件信息"""

    id: int
    """插件 ID"""
    name: str
    """插件名"""
    module: str
    """模块名"""
    description: str
    """简介"""
    usage: str
    """用法"""
    author: str
    """作者"""
    version: str
    """版本"""
    plugin_type: str
    """插件类型"""
    is_dir: bool
    """是否为文件夹插件"""


class StoreResponse(BaseModel):
    """插件商店响应"""

    install_module: list[str]
    """已安装的模块名列表"""
    plugin_list: list[StorePluginInfo]
    """插件列表"""


class InstallPluginRequest(BaseModel):
    """安装插件请求"""

    id: int
    """插件 ID"""


@router.get(
    "/get-plugin-store",
    response_model=APIResponse[StoreResponse],
    summary="获取插件商店列表",
)
async def get_plugin_store(user: AuthenticatedUser) -> APIResponse[StoreResponse]:
    """获取插件商店列表

    Returns:
        APIResponse[StoreResponse]: 插件商店列表
    """
    try:
        from zhenxun.builtin_plugins.plugin_store import StoreManager

        # 获取插件数据
        default_plugins, extra_plugins = await StoreManager.get_data()

        # 获取已安装的插件模块名
        import nonebot

        from zhenxun.models.plugin_info import PluginInfo

        installed_modules = []
        try:
            plugin_infos = await PluginInfo.all().values_list("module", flat=True)
            installed_modules = list(plugin_infos)
        except Exception:
            # 使用 nonebot 已加载的插件
            installed_modules = list(nonebot.get_loaded_plugins())

        # 合并所有插件
        all_plugins = default_plugins + extra_plugins

        # 转换为响应格式，添加 id 字段（使用索引作为 ID）
        plugin_list = [
            StorePluginInfo(
                id=idx,
                name=p.name,
                module=p.module,
                description=p.description,
                usage=p.usage,
                author=p.author,
                version=p.version,
                plugin_type=p.plugin_type.value,
                is_dir=p.is_dir,
            )
            for idx, p in enumerate(all_plugins)
        ]

        return success_response(
            data=StoreResponse(
                install_module=installed_modules,
                plugin_list=plugin_list,
            )
        )
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"获取插件商店列表失败：{e!s}", code=500)


@router.post(
    "/install",
    response_model=APIResponse[bool],
    summary="安装插件",
)
async def install_plugin(
    user: AuthenticatedUser, request: InstallPluginRequest
) -> APIResponse[bool]:
    """安装插件

    Args:
        request: 安装请求

    Returns:
        APIResponse[bool]: 是否安装成功
    """
    try:
        from zhenxun.builtin_plugins.plugin_store import StoreManager

        # 获取插件数据
        default_plugins, extra_plugins = await StoreManager.get_data()
        all_plugins = default_plugins + extra_plugins

        if request.id >= len(all_plugins):
            raise APIException("插件 ID 不存在", code=400)

        await StoreManager.add_plugin(str(request.id))

        return success_response(data=True, message="插件安装成功")
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"安装插件失败：{e!s}", code=500)


@router.post(
    "/update",
    response_model=APIResponse[bool],
    summary="更新插件",
)
async def update_plugin(
    user: AuthenticatedUser, request: InstallPluginRequest
) -> APIResponse[bool]:
    """更新插件

    Args:
        request: 更新请求

    Returns:
        APIResponse[bool]: 是否更新成功
    """
    try:
        from zhenxun.builtin_plugins.plugin_store import StoreManager

        # 获取插件数据
        default_plugins, extra_plugins = await StoreManager.get_data()
        all_plugins = default_plugins + extra_plugins

        if request.id >= len(all_plugins):
            raise APIException("插件 ID 不存在", code=400)

        await StoreManager.update_plugin(str(request.id))

        return success_response(data=True, message="插件更新成功")
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"更新插件失败：{e!s}", code=500)


@router.post(
    "/remove",
    response_model=APIResponse[bool],
    summary="移除插件",
)
async def remove_plugin(
    user: AuthenticatedUser, request: InstallPluginRequest
) -> APIResponse[bool]:
    """移除插件

    Args:
        request: 移除请求

    Returns:
        APIResponse[bool]: 是否移除成功
    """
    try:
        from zhenxun.builtin_plugins.plugin_store import StoreManager

        # 获取插件数据
        default_plugins, extra_plugins = await StoreManager.get_data()
        all_plugins = default_plugins + extra_plugins

        if request.id >= len(all_plugins):
            raise APIException("插件 ID 不存在", code=400)

        await StoreManager.remove_plugin(str(request.id))

        return success_response(data=True, message="插件移除成功")
    except APIException:
        raise
    except Exception as e:
        raise APIException(f"移除插件失败：{e!s}", code=500)
