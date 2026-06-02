"""插件相关模型"""

from pydantic import BaseModel, Field


class PluginInfo(BaseModel):
    """插件信息"""

    id: int = Field(..., description="插件 ID")
    module: str = Field(..., description="模块名")
    name: str = Field(..., description="插件名称")
    description: str = Field(default="", description="插件描述")
    author: str = Field(..., description="作者")
    version: str = Field(..., description="版本号")
    plugin_type: str = Field(..., description="插件类型")
    is_enabled: bool = Field(..., description="是否启用")
    allow_switch: bool = Field(default=True, description="是否允许开关")
    allow_setting: bool = Field(default=False, description="是否允许设置")
    is_builtin: bool = Field(default=False, description="是否内置插件")


class PluginListRequest(BaseModel):
    """插件列表请求"""

    search: str | None = Field(None, description="搜索关键词")
    status: bool | None = Field(None, description="状态过滤")
    plugin_type: str | None = Field(None, description="类型过滤")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=50, description="每页数量")


class PluginListResult(BaseModel):
    """插件列表结果"""

    items: list[PluginInfo] = Field(..., description="插件列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class PluginToggleRequest(BaseModel):
    """插件开关请求"""

    module: str = Field(..., description="模块名")
    enable: bool = Field(..., description="是否启用")


class PluginConfigItem(BaseModel):
    """插件配置项"""

    module: str = Field(..., description="模块名")
    key: str = Field(..., description="配置键")
    value: str = Field(..., description="配置值")
    description: str | None = Field(None, description="配置描述")


class PluginConfigResult(BaseModel):
    """插件配置结果"""

    module: str = Field(..., description="模块名")
    name: str = Field(..., description="插件名称")
    configs: list[PluginConfigItem] = Field(..., description="配置项列表")
