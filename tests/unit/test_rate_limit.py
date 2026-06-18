"""限流测试:超过频率限制返回 429 统一信封。"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from oncall_agent.api.schemas import ApiResponse


def _app_with_limit(limit: str) -> FastAPI:
    """构造一个带限流的最小 app(独立 limiter,避免污染全局)。"""
    app = FastAPI()
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(status_code=429, content=ApiResponse.fail("请求过于频繁").model_dump())

    @app.get("/_probe")
    @limiter.limit(limit)
    async def _probe(request: Request) -> dict:
        return {"ok": True}

    return app


def test_within_limit_ok():
    """限额内的请求正常返回 200。"""
    client = TestClient(_app_with_limit("3/minute"))
    for _ in range(3):
        assert client.get("/_probe").status_code == 200


def test_over_limit_returns_429_envelope():
    """超过限额返回 429 与统一信封。"""
    client = TestClient(_app_with_limit("2/minute"))
    client.get("/_probe")
    client.get("/_probe")
    resp = client.get("/_probe")  # 第 3 次,超过 2/minute

    assert resp.status_code == 429
    body = resp.json()
    assert body["success"] is False
    assert "频繁" in body["error"]
