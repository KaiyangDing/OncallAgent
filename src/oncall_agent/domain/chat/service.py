"""对话服务:编译 ReAct 图,提供多轮对话能力。

负责:
- 用注入的 checkpointer 编译图(接入会话记忆)
- 维护系统提示词(仅在会话开头注入一次)
- 修剪过长的消息历史,控制上下文规模
"""

from collections.abc import AsyncIterator

from langchain_core.messages import AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_qwq import ChatQwen
from langgraph.checkpoint.base import BaseCheckpointSaver

from oncall_agent.callbacks import TokenUsageCallback
from oncall_agent.context import track_token_usage
from oncall_agent.domain.chat.graph import build_chat_graph
from oncall_agent.domain.chat.prompts import SYSTEM_PROMPT


class ChatService:
    """多轮对话服务(基于 ReAct 图)。"""

    def __init__(
        self,
        model: ChatQwen,
        tools: list[BaseTool],
        checkpointer: BaseCheckpointSaver,
        max_history: int = 20,
    ) -> None:
        graph = build_chat_graph(model, tools, max_history=max_history)
        self._agent = graph.compile(checkpointer=checkpointer)

    async def chat(self, question: str, session_id: str) -> str:
        """非流式对话:返回完整回答。"""
        async with track_token_usage():
            result = await self._agent.ainvoke(
                self._build_input(question, session_id),
                config=self._config(session_id),
            )
            return result["messages"][-1].content

    async def chat_stream(self, question: str, session_id: str) -> AsyncIterator[str]:
        """流式对话:逐块产出回答文本片段。"""
        async with track_token_usage():
            async for chunk, _metadata in self._agent.astream(
                self._build_input(question, session_id),
                config=self._config(session_id),
                stream_mode="messages",
            ):
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    yield self._extract_text(chunk.content)

    @staticmethod
    def _extract_text(content: object) -> str:
        """从消息内容中提取纯文本(兼容 str 与分块 list 两种格式)。"""
        if isinstance(content, str):
            return content

        # 部分模型返回 content blocks 列表,提取其中的 text
        parts = []
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
        return "".join(parts)

    def _build_input(self, question: str, session_id: str) -> dict:
        """构造图输入:首轮带系统提示,后续仅追加用户消息。"""
        messages: list[BaseMessage] = []
        if self._is_new_session(session_id):
            messages.append(SystemMessage(content=SYSTEM_PROMPT))
        messages.append(HumanMessage(content=question))
        return {"messages": messages}

    def _is_new_session(self, session_id: str) -> bool:
        """该会话是否尚无历史(决定是否需要注入系统提示)。"""
        state = self._agent.get_state(self._config(session_id))
        return not state.values.get("messages")

    @staticmethod
    def _config(session_id: str) -> dict:
        """LangGraph 配置:用 session_id 作为 thread_id 隔离会话。"""
        return {
            "configurable": {"thread_id": session_id},
            "callbacks": [TokenUsageCallback()],
        }
