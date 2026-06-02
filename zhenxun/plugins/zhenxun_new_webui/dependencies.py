"""依赖注入"""

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from zhenxun.configs.config import Config

from .models.auth import User
from .utils.security import ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/zhenxun/api/v1/auth/login", auto_error=False
)


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """获取当前用户

    参数:
        token: JWT token

    返回:
        User: 用户信息

    异常:
        HTTPException: 认证失败时抛出 401 异常
    """
    if not token:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    try:
        payload = jwt.decode(
            token, Config.get_config("web-ui", "secret"), algorithms=[ALGORITHM]
        )
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的 token")
        return User(username=username)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token 验证失败：{e}")


def require_auth(user: User = Depends(get_current_user)) -> User:
    """要求用户已认证"""
    return user


# 类型别名
CurrentUser = Annotated[User, Depends(get_current_user)]
AuthenticatedUser = Annotated[User, Depends(require_auth)]
