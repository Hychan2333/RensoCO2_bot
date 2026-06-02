"""数据库相关模型"""

from pydantic import BaseModel, Field


class TableRowData(BaseModel):
    """表行数据"""

    id: int | str = Field(..., description="主键")
    data: dict = Field(..., description="行数据")


class TableDataResult(BaseModel):
    """表数据结果"""

    items: list[TableRowData] = Field(..., description="数据列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class SqlExecuteRequest(BaseModel):
    """SQL 执行请求"""

    sql: str = Field(..., description="SQL 语句")


class SqlExecuteResult(BaseModel):
    """SQL 执行结果"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    data: list[dict] | None = Field(None, description="返回数据")
    rows_affected: int | None = Field(None, description="影响的行数")
