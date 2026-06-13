"""LLM 工厂:构造通义千问对话模型实例。"""

from langchain_qwq import ChatQwen

from oncall_agent.settings import Settings


def create_chat_model(settings: Settings, *, streaming: bool = False) -> ChatQwen:
    """构造 ChatQwen 实例。

    Args:
        settings: 应用配置(提供 api_key、base_url、模型名)
        streaming: 是否启用流式输出
    """
    return ChatQwen(
        model=settings.chat_model,
        api_key=settings.dashscope_api_key.get_secret_value(),
        base_url=settings.dashscope_base_url,
        streaming=streaming,
        temperature=0.7,
    )
