"""Logs MCP 服务器:提供服务日志查询。

独立进程,通过 streamable-http 暴露工具,供主应用的 MCP 客户端连接。
运行:python mcp_servers/logs_server.py
"""

from fastmcp import FastMCP

from mcp_servers._fixtures import FAULT_LOGS, FAULT_SERVICE

mcp = FastMCP("logs")


@mcp.tool
def search_logs(service: str, level: str = "ERROR") -> dict:
    """查询指定服务的日志。

    Args:
        service: 服务名,例如 "data-sync-service"
        level: 最低日志级别,可选 "INFO" / "WARN" / "ERROR",默认 "ERROR"

    返回该服务匹配级别的日志条目,用于定位故障根因。
    """
    if service != FAULT_SERVICE:
        return {"service": service, "logs": [], "note": "无该服务的日志"}

    order = {"INFO": 0, "WARN": 1, "ERROR": 2}
    threshold = order.get(level, 2)
    matched = [log for log in FAULT_LOGS if order.get(log["level"], 0) >= threshold]

    return {
        "service": service,
        "level": level,
        "logs": matched,
        "total": len(matched),
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8002)
