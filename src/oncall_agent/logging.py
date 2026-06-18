"""日志配置(基于 loguru)。

关键原则:本模块 import 时不产生任何副作用。
日志的实际配置由 setup_logging() 显式触发,在应用启动时调用一次。
"""

import sys

from loguru import logger

from oncall_agent.context import request_id_var
from oncall_agent.settings import Settings


def setup_logging(settings: Settings) -> None:
    """配置全局 logger:移除默认处理器,挂载控制台 + 文件两个 sink。

    Args:
        settings: 应用配置,据此决定日志级别等。
    """
    logger.remove()

    # 每条日志自动注入当前请求的 request-id(无请求上下文时为 "-")
    logger.configure(patcher=lambda record: record["extra"].update(request_id=request_id_var.get()))

    level = "DEBUG" if settings.debug else "INFO"

    # 控制台:带颜色,便于本地开发
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<magenta>{extra[request_id]}</magenta> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=settings.debug,
    )

    # 文件:按天轮转,保留 7 天,异步写入
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        level="INFO",
        rotation="00:00",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=settings.debug,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{extra[request_id]} | {name}:{function}:{line} | {message}"
        ),
    )

    logger.info("日志系统初始化完成,级别={}", level)
