"""Replanner 节点:评估进展,决定继续 / 重规划 / 生成报告。"""

from collections.abc import Awaitable, Callable
from typing import Literal

from langchain_qwq import ChatQwen
from loguru import logger
from pydantic import BaseModel, Field

from oncall_agent.domain.diagnosis.prompts import REPLANNER_PROMPT
from oncall_agent.domain.diagnosis.state import DiagnosisState, format_past_steps

NodeFn = Callable[[DiagnosisState], Awaitable[dict]]

# 执行步数硬上限:超过则强制生成报告,防止无限循环
_MAX_STEPS = 6


class Decision(BaseModel):
    """Replanner 的结构化决策。"""

    action: Literal["continue", "replan", "respond"] = Field(
        description="下一步行动:continue 继续 / replan 调整计划 / respond 生成报告"
    )
    new_plan: list[str] = Field(
        default_factory=list,
        description="仅当 action 为 replan 时提供:替换剩余计划的新步骤列表",
    )


def make_replanner(model: ChatQwen) -> NodeFn:
    """工厂:返回绑定了模型的 replanner 节点。"""
    decide_chain = REPLANNER_PROMPT | model.with_structured_output(Decision)

    async def replanner(state: DiagnosisState) -> dict:
        """评估进展并决策。返回 {"plan": [...]} 调整计划,或 {"plan": []} 触发报告生成。"""
        past_steps = state["past_steps"]

        # 护栏:执行步数超限,强制收尾
        if len(past_steps) >= _MAX_STEPS:
            logger.warning("已执行 {} 步,达到上限,强制生成报告", len(past_steps))
            return {"plan": []}

        decision: Decision = await decide_chain.ainvoke(
            {
                "task": state["task"],
                "past_steps": format_past_steps(past_steps),
                "plan": ", ".join(state["plan"]) or "(无剩余步骤)",
            }
        )
        logger.info("Replanner 决策:{}", decision.action)

        if decision.action == "replan" and decision.new_plan:
            return {"plan": decision.new_plan}
        if decision.action == "respond":
            return {"plan": []}  # 清空计划 → 路由到报告节点
        return {}  # continue:不改状态,继续执行剩余计划

    return replanner
