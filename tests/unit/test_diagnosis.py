"""M5 单测:诊断节点的关键逻辑(用 mock LLM/工具,不联网)。"""

from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage

from oncall_agent.domain.diagnosis.executor import make_executor
from oncall_agent.domain.diagnosis.replanner import _MAX_STEPS, make_replanner
from oncall_agent.domain.diagnosis.state import format_past_steps


def test_format_past_steps_numbers_each_step():
    """已执行步骤被编号并带上结果。"""
    text = format_past_steps([("查告警", "发现 HighCPUUsage"), ("查指标", "CPU 95%")])

    assert "1. 查告警" in text
    assert "发现 HighCPUUsage" in text
    assert "2. 查指标" in text


async def test_replanner_forces_report_at_step_limit():
    """护栏:已执行步数达上限时,不调用 LLM,直接清空计划强制收尾。"""
    model = MagicMock()
    model.with_structured_output.return_value = MagicMock()
    replanner = make_replanner(model)

    past_steps = [(f"步骤{i}", "结果") for i in range(_MAX_STEPS)]
    result = await replanner(
        {"task": "t", "plan": ["还有一步"], "past_steps": past_steps, "report": ""}
    )

    assert result == {"plan": []}  # 清空计划 → 路由到报告
    model.with_structured_output.return_value.ainvoke.assert_not_called()  # 没问 LLM


async def test_executor_tolerates_unknown_tool():
    """容错:LLM 请求不存在的工具时,executor 不崩溃,回灌错误信息后正常结束。"""
    # 第一次:LLM 请求一个不存在的工具;第二次:LLM 给出最终答案
    bad_call = AIMessage(
        content="",
        tool_calls=[{"name": "no_such_tool", "args": {}, "id": "c1"}],
    )
    final = AIMessage(content="已处理")
    model = MagicMock()
    model.bind_tools.return_value.ainvoke = AsyncMock(side_effect=[bad_call, final])

    executor = make_executor(model, tools=[])
    result = await executor({"task": "t", "plan": ["执行某步"], "past_steps": [], "report": ""})

    assert result["plan"] == []  # 当前步已移除
    assert result["past_steps"] == [("执行某步", "已处理")]  # 容错后拿到最终答案
