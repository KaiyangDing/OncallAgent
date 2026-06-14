"""MCP 客户端:连接 MCP 服务器,加载其工具为 LangChain 工具。

设计要点:
- 工具懒加载并缓存,避免每次请求重连。
- 加载失败时返回空列表并记录,不抛异常(Agent 可降级为仅本地工具)。
- 失败状态不固化:下次请求会再次尝试加载(可恢复)。
"""

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from loguru import logger

from oncall_agent.settings import Settings


class MCPToolProvider:
    """按需加载并缓存 MCP 工具的提供者。"""

    def __init__(self, settings: Settings) -> None:
        self._config = {
            "monitor": {"url": settings.mcp_monitor_url, "transport": "streamable_http"},
            "logs": {"url": settings.mcp_logs_url, "transport": "streamable_http"},
        }
        self._tools: list[BaseTool] | None = None

    async def get_tools(self) -> list[BaseTool]:
        """返回 MCP 工具列表;已加载则用缓存,失败则返回空列表(可下次重试)。"""
        if self._tools is not None:
            return self._tools

        try:
            client = MultiServerMCPClient(self._config)
            tools = await client.get_tools()
            self._tools = tools
            logger.info("加载 MCP 工具成功,共 {} 个", len(tools))
            return tools
        except Exception as e:
            # 不固化失败:_tools 保持 None,下次请求会重试
            logger.warning("加载 MCP 工具失败,本次降级为仅本地工具:{}", e)
            return []
