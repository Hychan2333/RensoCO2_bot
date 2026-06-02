"""文件相关模型"""

from datetime import datetime

from pydantic import BaseModel, Field


class FileItem(BaseModel):
    """文件项"""

    name: str = Field(..., description="文件名")
    is_file: bool = Field(..., description="是否为文件")
    is_image: bool = Field(default=False, description="是否为图片")
    size: int | None = Field(None, description="文件大小（字节）")
    size_formatted: str | None = Field(None, description="格式化后的文件大小")
    mtime: datetime | None = Field(None, description="最后修改时间")
    mtime_formatted: str | None = Field(None, description="格式化后的最后修改时间")
    path: str = Field(..., description="完整路径")
    parent: str | None = Field(None, description="父路径")


class FileListResult(BaseModel):
    """文件列表结果"""

    files: list[FileItem] = Field(..., description="文件列表")
    current_path: str = Field(..., description="当前路径")
    path_segments: list[str] = Field(
        default_factory=list, description="路径段（面包屑导航）"
    )
    has_parent: bool = Field(default=False, description="是否有父目录")


class FileContent(BaseModel):
    """文件内容"""

    path: str = Field(..., description="文件路径")
    content: str = Field(..., description="文件内容")
    encoding: str = Field(default="utf-8", description="文件编码")


class FileOperation(BaseModel):
    """文件操作请求"""

    source_path: str = Field(..., description="源路径")
    dest_path: str | None = Field(None, description="目标路径")
    operation: str = Field(..., description="操作类型：delete, rename, move, copy")
    new_name: str | None = Field(None, description="新文件名（重命名用）")


class CreateFileRequest(BaseModel):
    """创建文件/文件夹请求"""

    parent_path: str = Field(..., description="父路径")
    name: str = Field(..., description="文件/文件夹名")


class SaveFileRequest(BaseModel):
    """保存文件请求"""

    file_path: str = Field(..., description="文件路径")
    content: str = Field(..., description="文件内容")


class DeleteFileRequest(BaseModel):
    """删除文件请求"""

    file_path: str = Field(..., description="文件路径")


class DeleteFolderRequest(BaseModel):
    """删除文件夹请求"""

    folder_path: str = Field(..., description="文件夹路径")


class RenameRequest(BaseModel):
    """重命名请求"""

    source_path: str = Field(..., description="源路径")
    new_name: str = Field(..., description="新名称")
