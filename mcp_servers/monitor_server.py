"""Monitor MCP 服务器:提供活动告警查询与服务指标查询。

独立进程,通过 streamable-http 暴露工具,供主应用的 MCP 客户端连接。
运行:python mcp_servers/monitor_server.py
"""

from fastmcp import FastMCP

from mcp_servers._fixtures import ACTIVE_ALERTS, FAULT_SERVICE, cpu_series

mcp = FastMCP("monitor")


@mcp.tool
def query_active_alerts() -> list[dict]:
    """查询当前所有活动告警。

    返回正在触发的告警列表,每条含告警名、严重级别、所属服务、描述与持续时间。
    用于诊断起点:先了解系统当前有哪些异常。
    """
    return ACTIVE_ALERTS


@mcp.tool
def query_cpu_metrics(service: str) -> dict:
    """查询指定服务的 CPU 使用率时间序列。

    Args:
        service: 服务名,例如 "data-sync-service"

    返回该服务最近的 CPU 使用率数据点(百分比)及统计摘要。
    """
    if service != FAULT_SERVICE:
        return {"service": service, "series": [], "note": "无该服务的指标数据"}

    series = cpu_series()
    peak = max(point["cpu_percent"] for point in series)
    return {
        "service": service,
        "series": series,
        "peak_cpu_percent": peak,
        "note": f"CPU 峰值 {peak}%,已持续高位",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
