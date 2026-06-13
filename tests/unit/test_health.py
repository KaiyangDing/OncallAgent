"""M1 测试:健康检查接口与全局异常处理。"""

from fastapi.testclient import TestClient

from oncall_agent.main import create_app


def test_health_check_returns_ok():
    """/health 返回 200 与统一信封,data 含服务信息。"""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["data"]["service"] == "OnCall Agent"
    assert body["error"] is None


def test_unhandled_exception_returns_500_envelope():
    """未捕获异常 → HTTP 500 + 统一失败信封。"""
    app = create_app()

    @app.get("/_test_boom")
    def _boom() -> None:
        raise ValueError("故意制造的错误")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/_test_boom")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "服务器内部错误"
    assert body["data"] is None
