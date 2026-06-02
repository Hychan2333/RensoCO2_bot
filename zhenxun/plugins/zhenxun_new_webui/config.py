"""WebUI Next 配置模块"""

from fastapi.middleware.cors import CORSMiddleware
import nonebot

app = nonebot.get_app()

# CORS 配置 - 开发环境允许常见端口
# 注意：allow_origins=["*"] 与 allow_credentials=True 不能同时使用
# 需要明确指定允许的源
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # 允许携带凭证（cookies、authorization headers 等）
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)
