"""文件路由"""

from fastapi.responses import JSONResponse

from ..dependencies import AuthenticatedUser
from ..exceptions import FileException
from ..models.file import (
    CreateFileRequest,
    DeleteFileRequest,
    DeleteFolderRequest,
    FileListResult,
    RenameRequest,
    SaveFileRequest,
)
from ..responses import APIResponse, error_response, success_response
from ..routing import WebUIRouter
from ..services.file_service import FileService

router = WebUIRouter(prefix="/file", tags=["文件管理"])


@router.get(
    "/list",
    response_model=APIResponse[FileListResult],
    summary="获取文件列表",
)
async def get_file_list(
    user: AuthenticatedUser, path: str | None = None
) -> APIResponse[FileListResult]:
    """获取指定路径下的文件列表

    Args:
        path: 路径，默认为根目录

    Returns:
        APIResponse[FileListResult]: 文件列表结果
    """
    result = await FileService.get_file_list(path)
    return success_response(data=result)


@router.get(
    "/read",
    summary="读取文件内容",
)
async def read_file(user: AuthenticatedUser, file_path: str, as_image: bool = False):
    """读取指定文件的内容

    Args:
        file_path: 文件路径
        as_image: 是否以图片方式读取（返回 base64）

    Returns:
        文件内容或错误响应
    """
    try:
        result = await FileService.read_file(file_path, as_image=as_image)
        return success_response(data=result)
    except FileException as e:
        # 直接返回 JSON 响应
        return JSONResponse(
            status_code=e.code,
            content=error_response(message=e.message, code=e.code).model_dump(),
        )


@router.post(
    "/save",
    response_model=APIResponse[bool],
    summary="保存文件内容",
)
async def save_file(
    user: AuthenticatedUser, request: SaveFileRequest
) -> APIResponse[bool]:
    """保存文件内容

    Args:
        request: 保存请求

    Returns:
        APIResponse[bool]: 是否保存成功
    """
    result = await FileService.save_file(request.file_path, request.content)
    return success_response(data=result, message="保存成功")


@router.post(
    "/delete",
    response_model=APIResponse[bool],
    summary="删除文件",
)
async def delete_file(
    user: AuthenticatedUser, request: DeleteFileRequest
) -> APIResponse[bool]:
    """删除指定文件

    Args:
        request: 删除请求

    Returns:
        APIResponse[bool]: 是否删除成功
    """
    result = await FileService.delete_file(request.file_path)
    return success_response(data=result, message="删除成功")


@router.post(
    "/delete-folder",
    response_model=APIResponse[bool],
    summary="删除文件夹",
)
async def delete_folder(
    user: AuthenticatedUser, request: DeleteFolderRequest
) -> APIResponse[bool]:
    """删除指定文件夹

    Args:
        request: 删除请求

    Returns:
        APIResponse[bool]: 是否删除成功
    """
    result = await FileService.delete_folder(request.folder_path)
    return success_response(data=result, message="删除成功")


@router.post(
    "/rename",
    response_model=APIResponse[bool],
    summary="重命名文件/文件夹",
)
async def rename(user: AuthenticatedUser, request: RenameRequest) -> APIResponse[bool]:
    """重命名文件或文件夹

    Args:
        request: 重命名请求

    Returns:
        APIResponse[bool]: 是否重命名成功
    """
    result = await FileService.rename(request.source_path, request.new_name)
    return success_response(data=result, message="重命名成功")


@router.post(
    "/create-file",
    response_model=APIResponse[bool],
    summary="创建文件",
)
async def create_file(
    user: AuthenticatedUser, request: CreateFileRequest
) -> APIResponse[bool]:
    """创建新文件

    Args:
        request: 创建请求

    Returns:
        APIResponse[bool]: 是否创建成功
    """
    result = await FileService.create_file(request.parent_path, request.name)
    return success_response(data=result, message="创建成功")


@router.post(
    "/create-folder",
    response_model=APIResponse[bool],
    summary="创建文件夹",
)
async def create_folder(
    user: AuthenticatedUser, request: CreateFileRequest
) -> APIResponse[bool]:
    """创建新文件夹

    Args:
        request: 创建请求

    Returns:
        APIResponse[bool]: 是否创建成功
    """
    result = await FileService.create_folder(request.parent_path, request.name)
    return success_response(data=result, message="创建成功")
