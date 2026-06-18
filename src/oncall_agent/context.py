"""请求级上下文:用 contextvar 在整个请求处理链路中传递 request-id。"""

from contextvars import ContextVar
from dataclasses import dataclass

# 存储当前请求的 request-id;默认 "-" 表示"不在请求上下文中"(如启动日志)
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


@dataclass
class TokenUsage:
    """累计 token 用量。"""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# 当前请求的 token 累加器(每个请求一份)
token_usage_var: ContextVar[TokenUsage | None] = ContextVar("token_usage", default=None)
