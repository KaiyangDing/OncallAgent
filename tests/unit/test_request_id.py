"""request-id 中间件测试:每个请求分配唯一 ID 并写入响应头。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from oncall_agent.middleware import REQUEST_ID_HEADER, request_middleware


def _app_with_middleware() -> FastAPI:
    """构造一个仅含中间件和一个探针路由的最小 app(不依赖 lifespan)。"""
    app = FastAPI()
    app.middleware("http")(request_middleware)

    @app.get("/_probe")
    def _probe() -> dict:
        return {"ok": True}

    return app


def test_response_has_request_id():
    """响应头携带自动生成的 request-id。"""
    client = TestClient(_app_with_middleware())
    resp = client.get("/_probe")
    assert REQUEST_ID_HEADER in resp.headers
    assert len(resp.headers[REQUEST_ID_HEADER]) == 8  # uuid4().hex[:8]


def test_each_request_gets_different_id():
    """不同请求分配不同的 request-id。"""
    client = TestClient(_app_with_middleware())
    id1 = client.get("/_probe").headers[REQUEST_ID_HEADER]
    id2 = client.get("/_probe").headers[REQUEST_ID_HEADER]
    assert id1 != id2


def test_client_provided_id_is_reused():
    """客户端传入的 request-id 被复用(便于跨服务串联)。"""
    client = TestClient(_app_with_middleware())
    resp = client.get("/_probe", headers={REQUEST_ID_HEADER: "my-trace-123"})
    assert resp.headers[REQUEST_ID_HEADER] == "my-trace-123"
