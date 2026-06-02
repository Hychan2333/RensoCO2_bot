"""文件服务"""

from datetime import datetime
import os
from pathlib import Path
import shutil

import aiofiles

from ..exceptions import FileException, ValidationException
from ..models.file import FileContent, FileItem, FileListResult
from ..utils.formatters import format_datetime, format_file_size
from ..utils.path_validator import generate_path_segments, validate_path_secure


class FileService:
    """文件服务"""

    IMAGE_TYPE = [
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "webp",
        "svg",
        "ico",
        "tiff",
        "tif",
    ]

    @staticmethod
    def get_mime_type(ext: str) -> str:
        """获取图片的 MIME 类型

        参数:
            ext: 文件扩展名

        返回:
            str: MIME 类型
        """
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        return mime_types.get(ext.lower(), "application/octet-stream")

    @staticmethod
    def get_root_dir() -> Path:
        """获取根目录

        返回:
            Path: 根目录
        """
        return Path().resolve()

    @staticmethod
    async def get_file_list(path: str | None = None) -> FileListResult:
        """获取文件列表

        参数:
            path: 路径

        返回:
            FileListResult: 文件列表结果
        """
        root_dir = FileService.get_root_dir()
        validated_path, error = validate_path_secure(path, root_dir)
        if error or not validated_path:
            raise ValidationException(error or "无效的路径")

        if not validated_path.exists():
            raise FileException("路径不存在")

        files = []
        for file in os.listdir(validated_path):
            file_path = validated_path / file
            is_file = file_path.is_file()
            is_image = is_file and any(
                file.endswith(f".{t}") for t in FileService.IMAGE_TYPE
            )

            # 获取文件/文件夹的 stat 信息
            try:
                stat = file_path.stat()
                file_size = stat.st_size if is_file else None
                file_mtime = stat.st_mtime
            except Exception:
                # 如果无法获取 stat 信息，使用默认值
                file_size = None
                file_mtime = None

            files.append(
                FileItem(
                    name=file,
                    is_file=is_file,
                    is_image=is_image,
                    size=file_size,
                    size_formatted=format_file_size(file_size),
                    mtime=datetime.fromtimestamp(file_mtime)
                    if file_mtime > 0
                    else None,
                    mtime_formatted=format_datetime(file_mtime)
                    if file_mtime > 0
                    else None,
                    path=str(file_path),
                    parent=str(validated_path) if validated_path != root_dir else None,
                )
            )

        # 排序：文件夹在前，然后按名称排序
        files.sort(key=lambda f: (not f.is_file, f.name.lower()))

        return FileListResult(
            files=files,
            current_path=str(validated_path),
            path_segments=generate_path_segments(
                str(validated_path.relative_to(root_dir))
            ),
            has_parent=validated_path != root_dir,
        )

    @staticmethod
    def is_text_file(file_path: Path, sample_size: int = 8192) -> bool:
        """检测文件是否为文本文件

        参数:
            file_path: 文件路径
            sample_size: 采样大小

        返回:
            bool: 是否为文本文件
        """
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(sample_size)
                # 检查是否包含常见的二进制文件标记
                # PNG: 89 50 4E 47, JPEG: FF D8 FF
                if chunk.startswith(b"\x89PNG") or chunk.startswith(b"\xff\xd8\xff"):
                    return False
                # 检查是否包含空字节（二进制文件的常见特征）
                if b"\x00" in chunk:
                    return False
                # 尝试解码为 UTF-8
                try:
                    chunk.decode("utf-8")
                    return True
                except UnicodeDecodeError:
                    # 尝试其他常见编码
                    for encoding in ["gbk", "latin-1", "cp437"]:
                        try:
                            chunk.decode(encoding)
                            return True
                        except UnicodeDecodeError:
                            continue
                    return False
        except Exception:
            return False

    @staticmethod
    def is_image_file(file_path: Path) -> bool:
        """检测文件是否为图片文件

        参数:
            file_path: 文件路径

        返回:
            bool: 是否为图片文件
        """
        ext = file_path.suffix.lower()
        return ext in [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
            ".svg",
            ".ico",
            ".tiff",
            ".tif",
        ]

    @staticmethod
    async def read_file(file_path: str, as_image: bool = False) -> FileContent:
        """读取文件内容

        参数:
            file_path: 文件路径
            as_image: 是否以图片方式读取（返回 base64）

        返回:
            FileContent: 文件内容

        异常:
            FileException: 文件操作失败
        """
        import base64

        root_dir = FileService.get_root_dir()
        validated_path, error = validate_path_secure(file_path, root_dir)
        if error or not validated_path:
            raise ValidationException(error or "无效的路径")

        if not validated_path.exists():
            raise FileException("文件不存在")

        if validated_path.is_dir():
            raise FileException("不能读取目录")

        # 如果请求以图片方式读取
        if as_image or FileService.is_image_file(validated_path):
            try:
                with open(validated_path, "rb") as f:
                    image_data = f.read()
                # 转换为 base64
                base64_data = base64.b64encode(image_data).decode("utf-8")
                # 获取 MIME 类型
                mime_type = FileService.get_mime_type(validated_path.suffix)
                return FileContent(
                    path=str(validated_path),
                    content=f"data:{mime_type};base64,{base64_data}",
                    encoding="base64",
                )
            except Exception as e:
                raise FileException(f"读取图片文件失败：{e!s}")

        # 检测是否为文本文件
        if not FileService.is_text_file(validated_path):
            raise FileException("不支持读取二进制文件")

        # 尝试多种编码读取文本文件
        encodings = ["utf-8", "gbk", "utf-8-sig", "latin-1"]
        for encoding in encodings:
            try:
                content = validated_path.read_text(encoding=encoding)
                return FileContent(
                    path=str(validated_path),
                    content=content,
                    encoding=encoding,
                )
            except (UnicodeDecodeError, LookupError):
                continue

        raise FileException("文件编码不支持")

    @staticmethod
    async def save_file(file_path: str, content: str) -> bool:
        """保存文件内容

        参数:
            file_path: 文件路径
            content: 文件内容

        返回:
            bool: 是否保存成功

        异常:
            FileException: 文件操作失败
        """
        root_dir = FileService.get_root_dir()
        validated_path, error = validate_path_secure(file_path, root_dir)
        if error or not validated_path:
            raise ValidationException(error or "无效的路径")

        try:
            async with aiofiles.open(str(validated_path), "w", encoding="utf-8") as f:
                await f.write(content)
            return True
        except Exception as e:
            raise FileException(f"保存文件失败：{e!s}")

    @staticmethod
    async def delete_file(file_path: str) -> bool:
        """删除文件

        参数:
            file_path: 文件路径

        返回:
            bool: 是否删除成功

        异常:
            FileException: 文件操作失败
        """
        root_dir = FileService.get_root_dir()
        validated_path, error = validate_path_secure(file_path, root_dir)
        if error or not validated_path:
            raise ValidationException(error or "无效的路径")

        if not validated_path.exists():
            raise FileException("文件不存在")

        if validated_path.is_dir():
            raise FileException("不能删除目录")

        try:
            validated_path.unlink()
            return True
        except Exception as e:
            raise FileException(f"删除文件失败：{e!s}")

    @staticmethod
    async def delete_folder(folder_path: str) -> bool:
        """删除文件夹

        参数:
            folder_path: 文件夹路径

        返回:
            bool: 是否删除成功

        异常:
            FileException: 文件操作失败
        """
        root_dir = FileService.get_root_dir()
        validated_path, error = validate_path_secure(folder_path, root_dir)
        if error or not validated_path:
            raise ValidationException(error or "无效的路径")

        if not validated_path.exists():
            raise FileException("文件夹不存在")

        if validated_path.is_file():
            raise FileException("路径指向的是文件，不是文件夹")

        try:
            shutil.rmtree(validated_path)
            return True
        except Exception as e:
            raise FileException(f"删除文件夹失败：{e!s}")

    @staticmethod
    async def rename(source_path: str, new_name: str) -> bool:
        """重命名文件/文件夹

        参数:
            source_path: 源路径
            new_name: 新名称

        返回:
            bool: 是否重命名成功

        异常:
            FileException: 文件操作失败
        """
        root_dir = FileService.get_root_dir()
        validated_path, error = validate_path_secure(source_path, root_dir)
        if error or not validated_path:
            raise ValidationException(error or "无效的路径")

        if not validated_path.exists():
            raise FileException("文件/文件夹不存在")

        new_path = validated_path.parent / new_name

        # 验证新路径是否安全
        new_validated, error = validate_path_secure(str(new_path), root_dir)
        if error or not new_validated:
            raise ValidationException("新路径不合法")

        try:
            validated_path.rename(new_path)
            return True
        except Exception as e:
            raise FileException(f"重命名失败：{e!s}")

    @staticmethod
    async def create_file(parent_path: str, name: str) -> bool:
        """创建文件

        参数:
            parent_path: 父路径
            name: 文件名

        返回:
            bool: 是否创建成功

        异常:
            FileException: 文件操作失败
        """
        root_dir = FileService.get_root_dir()
        validated_path, error = validate_path_secure(parent_path, root_dir)
        if error or not validated_path:
            raise ValidationException(error or "无效的路径")

        if not validated_path.exists() or not validated_path.is_dir():
            raise FileException("父路径不存在或不是目录")

        file_path = validated_path / name

        # 验证新路径是否安全
        new_validated, error = validate_path_secure(str(file_path), root_dir)
        if error or not new_validated:
            raise ValidationException("文件路径不合法")

        if file_path.exists():
            raise FileException("文件已存在")

        try:
            file_path.touch()
            return True
        except Exception as e:
            raise FileException(f"创建文件失败：{e!s}")

    @staticmethod
    async def create_folder(parent_path: str, name: str) -> bool:
        """创建文件夹

        参数:
            parent_path: 父路径
            name: 文件夹名

        返回:
            bool: 是否创建成功

        异常:
            FileException: 文件操作失败
        """
        root_dir = FileService.get_root_dir()
        validated_path, error = validate_path_secure(parent_path, root_dir)
        if error or not validated_path:
            raise ValidationException(error or "无效的路径")

        if not validated_path.exists() or not validated_path.is_dir():
            raise FileException("父路径不存在或不是目录")

        folder_path = validated_path / name

        # 验证新路径是否安全
        new_validated, error = validate_path_secure(str(folder_path), root_dir)
        if error or not new_validated:
            raise ValidationException("文件夹路径不合法")

        if folder_path.exists():
            raise FileException("文件夹已存在")

        try:
            folder_path.mkdir()
            return True
        except Exception as e:
            raise FileException(f"创建文件夹失败：{e!s}")
