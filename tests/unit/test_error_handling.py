"""错误处理测试:HTTPException 与未捕获异常都返回统一信封。"""

from fastapi import HTTPException
from fastapi.testclient import TestClient

from oncall_agent.main import create_app


def test_http_exception_uses_envelope():
    """主动抛出的 HTTPException 转为统一信封,保留状态码。"""
    app = create_app()

    @app.get("/_test_400")
    def _bad() -> None:
        raise HTTPException(status_code=400, detail="参数有误")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/_test_400")

    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"] == "参数有误"
    assert body["data"] is None


def test_unhandled_exception_uses_envelope():
    """未捕获异常返回 500 + 统一信封,且不泄露内部细节。"""
    app = create_app()

    @app.get("/_test_500")
    def _boom() -> None:
        raise ValueError("内部数据库连接串 xxx")  # 模拟含敏感信息的异常

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/_test_500")

    assert resp.status_code == 500
    body = resp.json()
    assert body["success"] is False
    assert body["error"] == "服务器内部错误"  # 笼统信息
    assert "数据库连接串" not in body["error"]  # 不泄露内部细节