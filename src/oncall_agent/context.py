"""请求级上下文:用 contextvar 在整个请求处理链路中传递 request-id。"""

from contextvars import ContextVar

# 存储当前请求的 request-id;默认 "-" 表示"不在请求上下文中"(如启动日志)
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
