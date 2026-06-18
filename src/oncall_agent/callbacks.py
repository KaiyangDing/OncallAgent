"""LangChain 回调:收集每次 LLM 调用的 token 用量,累加到当前请求上下文。"""

from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from oncall_agent.context import token_usage_var


class TokenUsageCallback(BaseCallbackHandler):
    """每次 LLM 调用结束时,把 token 用量累加到当前请求的累加器。"""

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        usage = token_usage_var.get()
        if usage is None:
            return  # 不在统计上下文中,跳过

        # 从 LLM 结果里提取 usage_metadata(每代结果的最后一条 generation)
        for generations in response.generations:
            for gen in generations:
                message = getattr(gen, "message", None)
                meta = getattr(message, "usage_metadata", None) if message else None
                if meta:
                    usage.input_tokens += meta.get("input_tokens", 0)
                    usage.output_tokens += meta.get("output_tokens", 0)
