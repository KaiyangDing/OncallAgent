"""FastAPI 应用入口。

采用应用工厂模式:create_app() 构造并配置 app。
所有资源初始化集中在 lifespan,模块 import 不产生副作用。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from oncall_agent.api import health
from oncall_agent.api.schemas import ApiResponse
from oncall_agent.logging import setup_logging
from oncall_agent.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期:启动时初始化资源,关闭时释放。"""
    settings: Settings = get_settings()
    setup_logging(settings)
    logger.info("{} v{} 启动中...", settings.app_name, settings.app_version)

    yield

    logger.info("{} 已关闭", settings.app_name)


def create_app() -> FastAPI:
    """构造并配置 FastAPI 应用。"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.include_router(health.router)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """兜底异常处理:记录日志并返回统一的 500 响应。"""
        logger.exception("未处理异常: {} {}", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=ApiResponse.fail("服务器内部错误").model_dump(),
        )

    return app


# uvicorn 入口:oncall_agent.main:app
app = create_app()
