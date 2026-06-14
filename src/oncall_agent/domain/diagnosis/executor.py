"""Executor 节点:执行计划中的当前步骤,调用工具获取数据。

内部是一个小型 ReAct 循环(model ⇄ tools),复用 M3 已掌握的模式,
不依赖正在迁移的预制 agent 入口,保持可控。
"""

from collections.abc import Awaitable, Callable

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_qwq import ChatQwen
from loguru import logger

from oncall_agent.domain.diagnosis.prompts import EXECUTOR_SYSTEM
from oncall_agent.domain.diagnosis.state import DiagnosisState, format_past_steps

NodeFn = Callable[[DiagnosisState], Awaitable[dict]]

# 单步内最多的工具调用轮数,防止异常情况下无限循环
_MAX_TOOL_ROUNDS = 5


def make_executor(model: ChatQwen, tools: list[BaseTool]) -> NodeFn:
    """工厂:返回绑定了模型与工具的 executor 节点。"""
    model_with_tools = model.bind_tools(tools)
    tools_by_name = {tool.name: tool for tool in tools}

    async def executor(state: DiagnosisState) -> dict:
        """执行计划中的第一个步骤,记录结果。"""
        plan = state["plan"]
        if not plan:
            return {}

        current_step = plan[0]
        logger.info("执行步骤:{}", current_step)

        # 把已执行步骤的结果作为上下文,避免 Executor "失忆"导致跑偏
        past_steps = state["past_steps"]
        context = format_past_steps(past_steps) if past_steps else "(无)"

        messages: list[AnyMessage] = [
            SystemMessage(content=EXECUTOR_SYSTEM),
            HumanMessage(
                content=f"已完成的步骤及结果:\n{context}\n\n现在请执行当前步骤:{current_step}"
            ),
        ]

        # ReAct 循环:LLM 决策 → 调工具 → 回灌结果 → 直到不再调工具
        for _ in range(_MAX_TOOL_ROUNDS):
            response = await model_with_tools.ainvoke(messages)
            messages.append(response)

            if not response.tool_calls:
                break

            for call in response.tool_calls:
                tool = tools_by_name.get(call["name"])
                if tool is None:
                    # LLM 想调用不存在的工具:回灌错误信息,让它改用可用工具
                    output = f"工具 '{call['name']}' 不存在。可用工具:{list(tools_by_name)}"
                else:
                    output = await tool.ainvoke(call["args"])
                messages.append(ToolMessage(content=str(output), tool_call_id=call["id"]))

        answer = messages[-1].content

        return {
            "plan": plan[1:],
            "past_steps": [(current_step, answer)],
        }

    return executor
