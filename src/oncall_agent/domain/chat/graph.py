"""对话 Agent:手搭 ReAct 循环图(model ↔ tools)。

图结构:
    START → model ──有 tool_call──→ tools ──→ model(循环)
                  └──无 tool_call──→ END
"""

from collections.abc import Sequence
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, RemoveMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_qwq import ChatQwen
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


class ChatState(TypedDict):
    """对话状态:一个会随对话追加的消息列表。"""

    messages: Annotated[Sequence[BaseMessage], add_messages]


def build_chat_graph(model: ChatQwen, tools: list[BaseTool], max_history: int = 20):
    """构造对话 ReAct 图。

    Args:
        model: 对话模型(将绑定工具)
        tools: Agent 可用的工具列表
        max_history: 历史消息上限(不含系统消息),超出则修剪最旧的
    """
    model_with_tools = model.bind_tools(tools)

    def trim_history(state: ChatState) -> dict:
        """修剪节点:历史超过上限时,删除最旧的非系统消息。"""
        messages = state["messages"]
        if len(messages) <= max_history:
            return {}

        # 第一条通常是系统消息,需保留;只在其余消息中删最旧的
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        non_system = [m for m in messages if not isinstance(m, SystemMessage)]

        # 计算要删多少条非系统消息
        keep = max_history - len(system_msgs)
        to_remove = non_system[:-keep] if keep > 0 else non_system

        return {"messages": [RemoveMessage(id=m.id) for m in to_remove]}

    async def call_model(state: ChatState) -> dict:
        """model 节点:让 LLM 基于当前消息历史生成回复(可能含工具调用)。"""
        response = await model_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: ChatState) -> str:
        """条件路由:最后一条 AI 消息若请求调用工具,转 tools,否则结束。"""
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"

        return END

    graph = StateGraph(ChatState)
    graph.add_node("trim", trim_history)
    graph.add_node("model", call_model)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "trim")
    graph.add_edge("trim", "model")
    graph.add_conditional_edges("model", should_continue, ["tools", END])
    graph.add_edge("tools", "trim")

    return graph
