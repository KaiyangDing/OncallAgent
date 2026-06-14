"""M4 单测:MCP 工具提供者的缓存与失败降级(不连真实 MCP 服务器)。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from oncall_agent.infra import mcp as mcp_module
from oncall_agent.infra.mcp import MCPToolProvider
from oncall_agent.settings import Settings


def _provider() -> MCPToolProvider:
    return MCPToolProvider(Settings())


async def test_get_tools_success_and_cached(monkeypatch: pytest.MonkeyPatch):
    """加载成功后缓存:第二次不再重新构造客户端。"""
    fake_tool = MagicMock()
    fake_client = MagicMock()
    fake_client.get_tools = AsyncMock(return_value=[fake_tool])
    client_ctor = MagicMock(return_value=fake_client)
    monkeypatch.setattr(mcp_module, "MultiServerMCPClient", client_ctor)

    provider = _provider()
    first = await provider.get_tools()
    second = await provider.get_tools()

    assert first == [fake_tool]
    assert second == [fake_tool]
    client_ctor.assert_called_once()  # 缓存生效,只构造了一次


async def test_get_tools_failure_returns_empty_and_recoverable(
    monkeypatch: pytest.MonkeyPatch,
):
    """加载失败:返回空列表且不固化失败,下次可重试。"""
    failing_ctor = MagicMock(side_effect=RuntimeError("连接失败"))
    monkeypatch.setattr(mcp_module, "MultiServerMCPClient", failing_ctor)

    provider = _provider()
    result = await provider.get_tools()

    assert result == []
    # 失败未固化:再次调用会再次尝试(构造被再次调用)
    await provider.get_tools()
    assert failing_ctor.call_count == 2
