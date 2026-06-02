"""认证路由"""

from ..models.auth import LoginRequest, LoginResponse
from ..responses import APIResponse, success_response
from ..routing import WebUIRouter
from ..services.auth_service import AuthService
from ..utils.security import create_access_token

router = WebUIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=APIResponse[LoginResponse], summary="用户登录")
async def login(request: LoginRequest) -> APIResponse[LoginResponse]:
    """用户登录接口"""
    response = AuthService.login(request)
    return success_response(data=response, message="登录成功")


@router.get("/verify", response_model=APIResponse[dict], summary="验证 Token")
async def verify_token(token: str) -> APIResponse[dict]:
    """验证 Token 是否有效"""
    username = AuthService.verify_token(token)
    return success_response(data={"valid": True, "username": username})


@router.post(
    "/refresh",
    response_model=APIResponse[LoginResponse],
    summary="刷新 Token",
)
async def refresh_token(token: str) -> APIResponse[LoginResponse]:
    """刷新访问令牌"""
    username = AuthService.verify_token(token)
    new_token = create_access_token(username)
    return success_response(
        data=LoginResponse(
            access_token=new_token, token_type="bearer", expires_in=1800
        ),
        message="Token 刷新成功",
    )
