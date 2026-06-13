"""API 请求 / 响应契约。

全项目统一一种响应信封 ApiResponse,前端只需按一种格式解析。
"""

from pydantic import BaseModel


class ApiResponse[T](BaseModel):
    """统一响应信封。

    - success: 业务是否成功(与 HTTP 状态码语义一致,不再自相矛盾)
    - data: 成功时的载荷,失败时为 None
    - error: 失败时的人类可读错误信息,成功时为 None
    """

    success: bool
    data: T | None = None
    error: str | None = None

    @classmethod
    def ok(cls, data: T | None = None) -> "ApiResponse[T]":
        """构造成功响应。"""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "ApiResponse[T]":
        """构造失败响应。"""
        return cls(success=False, error=error)


class HealthData(BaseModel):
    """健康检查载荷。"""

    service: str
    version: str
    status: str
