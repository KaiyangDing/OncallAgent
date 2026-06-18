"""token 用量统计测试:callback 正确累加到当前请求的累加器。"""

from unittest.mock import MagicMock

from oncall_agent.callbacks import TokenUsageCallback
from oncall_agent.context import TokenUsage, token_usage_var


def _llm_result_with_usage(input_tokens: int, output_tokens: int) -> MagicMock:
    """构造一个带 usage_metadata 的假 LLMResult。"""
    message = MagicMock()
    message.usage_metadata = {"input_tokens": input_tokens, "output_tokens": output_tokens}
    gen = MagicMock()
    gen.message = message
    result = MagicMock()
    result.generations = [[gen]]
    return result


def test_callback_accumulates_tokens():
    """单次 LLM 调用的 token 被累加到累加器。"""
    usage = TokenUsage()
    token = token_usage_var.set(usage)
    try:
        TokenUsageCallback().on_llm_end(_llm_result_with_usage(100, 30))
        assert usage.input_tokens == 100
        assert usage.output_tokens == 30
        assert usage.total_tokens == 130
    finally:
        token_usage_var.reset(token)


def test_callback_accumulates_across_calls():
    """多次 LLM 调用累加到同一累加器(模拟一次诊断多次调用)。"""
    usage = TokenUsage()
    token = token_usage_var.set(usage)
    try:
        cb = TokenUsageCallback()
        cb.on_llm_end(_llm_result_with_usage(100, 30))
        cb.on_llm_end(_llm_result_with_usage(50, 20))
        assert usage.input_tokens == 150
        assert usage.output_tokens == 50
    finally:
        token_usage_var.reset(token)


def test_callback_noop_without_context():
    """不在请求上下文(累加器为 None)时,callback 安全跳过不报错。"""
    # 确保当前没有累加器
    assert token_usage_var.get() is None
    # 不应抛异常
    TokenUsageCallback().on_llm_end(_llm_result_with_usage(100, 30))
