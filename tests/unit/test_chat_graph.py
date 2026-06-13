"""M3 单测:对话图的路由与修剪逻辑(用 mock LLM,不联网)。"""

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage

from oncall_agent.domain.chat.graph import ChatState, build_chat_graph


def _trim_node(max_history: int):
    """从图里取出 trim 节点函数,单独测试它。"""
    model = MagicMock()
    model.bind_tools.return_value = model
    graph = build_chat_graph(model, tools=[], max_history=max_history)
    return graph.nodes["trim"].runnable.func


def test_trim_keeps_history_within_limit():
    """未超限:不删除任何消息(返回空更新)。"""
    trim = _trim_node(max_history=10)
    state: ChatState = {"messages": [HumanMessage(content="hi"), AIMessage(content="hello")]}

    result = trim(state)

    assert result == {}


def test_trim_removes_oldest_when_over_limit():
    """超限:删除最旧的非系统消息,保留系统消息。"""
    trim = _trim_node(max_history=2)
    messages = [
        SystemMessage(content="sys", id="sys"),
        HumanMessage(content="q1", id="h1"),
        AIMessage(content="a1", id="a1"),
        HumanMessage(content="q2", id="h2"),
    ]
    state: ChatState = {"messages": messages}

    result = trim(state)

    removed_ids = {m.id for m in result["messages"]}
    assert all(isinstance(m, RemoveMessage) for m in result["messages"])
    assert "sys" not in removed_ids  # 系统消息不删
    assert "h1" in removed_ids  # 最旧的被删
