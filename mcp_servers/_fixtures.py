"""Mock 数据剧本:所有 MCP 服务器共享同一套故障故事,保证一致性。

故障主角:data-sync-service 发生 HighCPUUsage,CPU 爬升 + 同步任务堆积。
"""

# 故障服务名(全剧本统一引用)
FAULT_SERVICE = "data-sync-service"

# 当前活动告警(monitor 的 query_active_alerts 返回)
ACTIVE_ALERTS = [
    {
        "alert_name": "HighCPUUsage",
        "severity": "critical",
        "service": FAULT_SERVICE,
        "description": "CPU 使用率持续超过 80%",
        "duration": "15m",
    },
]


def cpu_series() -> list[dict]:
    """生成 CPU 使用率时间序列:从正常爬升到 90%+(对齐告警)。"""
    values = [12, 15, 14, 30, 55, 78, 88, 92, 95, 91]
    return [{"minute": i, "cpu_percent": v} for i, v in enumerate(values)]


# 故障服务的错误日志(logs 的 search_logs 返回)
FAULT_LOGS = [
    {"time": "10:02:11", "level": "WARN", "message": "sync task queue length = 1200, growing"},
    {"time": "10:03:45", "level": "WARN", "message": "sync worker pool exhausted, tasks waiting"},
    {"time": "10:05:02", "level": "ERROR", "message": "sync task timeout after 30s, retrying"},
]
