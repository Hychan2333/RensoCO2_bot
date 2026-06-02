"""数据库路由"""

from ..dependencies import AuthenticatedUser
from ..models.database import (
    SqlExecuteRequest,
    SqlExecuteResult,
    TableDataResult,
)
from ..responses import APIResponse, error_response, success_response
from ..routing import WebUIRouter
from ..services.database_service import DatabaseService

router = WebUIRouter(prefix="/database", tags=["数据库"])


@router.get(
    "/tables",
    response_model=APIResponse[list[str]],
    summary="获取表列表",
)
async def get_table_list(user: AuthenticatedUser) -> APIResponse[list[str]]:
    """获取数据库表列表"""
    result = await DatabaseService.get_table_list()
    return success_response(data=result)


@router.get(
    "/tables/{table_name}/columns",
    response_model=APIResponse[list[dict]],
    summary="获取表字段",
)
async def get_table_columns(
    user: AuthenticatedUser, table_name: str
) -> APIResponse[list[dict]]:
    """获取指定表的字段列表"""
    result = await DatabaseService.get_table_columns(table_name)
    return success_response(data=result)


@router.get(
    "/tables/{table_name}/data",
    response_model=APIResponse[TableDataResult],
    summary="获取表数据",
)
async def get_table_data(
    user: AuthenticatedUser,
    table_name: str,
    page: int = 1,
    page_size: int = 50,
) -> APIResponse[TableDataResult]:
    """获取指定表的数据"""
    result = await DatabaseService.get_table_data(table_name, page, page_size)
    return success_response(data=result)


@router.post(
    "/execute",
    response_model=APIResponse[SqlExecuteResult],
    summary="执行 SQL",
)
async def execute_sql(
    user: AuthenticatedUser, request: SqlExecuteRequest
) -> APIResponse[SqlExecuteResult]:
    """执行 SQL 查询"""
    try:
        result = await DatabaseService.execute_sql(request)
        return success_response(data=result)
    except Exception as e:
        # SQL 执行错误，返回 400
        return error_response(
            message=f"SQL 执行错误：{e!s}",
            code=400,
            data=SqlExecuteResult(
                success=False,
                message=f"SQL 执行错误：{e!s}",
                data=None,
                rows_affected=None,
            ),
        )
