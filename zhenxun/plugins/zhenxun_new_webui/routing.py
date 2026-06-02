"""WebUI 路由默认配置。"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from .exceptions import APIException
from .responses import error_response


class WebUIRoute(APIRoute):
    """将 WebUI 业务异常转换为统一 JSON 响应。"""

    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request):
            try:
                return await original_route_handler(request)
            except APIException as exc:
                return JSONResponse(
                    status_code=exc.code,
                    content=error_response(
                        message=exc.message,
                        code=exc.code,
                        data=exc.data,
                    ).model_dump(),
                )

        return custom_route_handler


class WebUIRouter(APIRouter):
    """带 WebUI 默认响应配置的 APIRouter。"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default_response_class", JSONResponse)
        kwargs.setdefault("route_class", WebUIRoute)
        super().__init__(*args, **kwargs)
