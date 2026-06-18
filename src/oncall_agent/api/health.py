"""健康检查接口。"""

from fastapi import APIRouter

# from loguru import logger
from oncall_agent.api.schemas import ApiResponse, HealthData
from oncall_agent.settings import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthData])
def health_check() -> ApiResponse[HealthData]:
    """存活检查:返回服务名、版本与状态。

    M1 阶段仅报告服务自身状态;接入外部依赖后会扩展为依赖健康检查。
    """
    # logger.info("健康检查被调用")  # ← 临时加这行验证 request-id
    settings: Settings = get_settings()
    return ApiResponse.ok(
        HealthData(
            service=settings.app_name,
            version=settings.app_version,
            status="ok",
        )
    )
