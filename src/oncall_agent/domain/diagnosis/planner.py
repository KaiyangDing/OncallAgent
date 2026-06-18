"""Planner 节点:基于知识库经验,把诊断任务拆解为分步计划。"""

from collections.abc import Awaitable, Callable

from langchain_core.tools import BaseTool
from langchain_qwq import ChatQwen
from loguru import logger
from pydantic import BaseModel, Field

from oncall_agent.domain.diagnosis.prompts import PLANNER_PROMPT
from oncall_agent.domain.diagnosis.state import DiagnosisState
from oncall_agent.domain.knowledge.retriever import RetrievalService

NodeFn = Callable[[DiagnosisState], Awaitable[dict]]


class Plan(BaseModel):
    """诊断计划:有序的步骤列表。"""

    steps: list[str] = Field(description="按顺序执行的诊断步骤,每步说明要做什么、用哪个工具")


def make_planner(model: ChatQwen, tools: list[BaseTool], retrieval: RetrievalService) -> NodeFn:
    """工厂:返回绑定了 LLM、工具清单与检索服务的 planner 节点。"""
    tools_desc = "\n".join(f"- {tool.name}: {tool.description}" for tool in tools)
    planner_chain = PLANNER_PROMPT | model.with_structured_output(Plan)

    async def planner(state: DiagnosisState) -> dict:
        """先检索经验,再据此制定诊断计划。"""
        task = state["task"]
        experience = retrieval.retrieve(task)

        plan: Plan | None = await planner_chain.ainvoke(
            {"task": task, "experience": experience, "tools": tools_desc}
        )

        if plan is None or not plan.steps:
            logger.warning("Planner 未能生成有效计划,使用默认诊断步骤")
            return {
                "plan": [
                    "使用 query_active_alerts 查询当前活动告警",
                    "针对告警涉及的服务,查询其指标与日志",
                    "检索知识库获取处理建议,综合生成诊断报告",
                ]
            }

        logger.info("诊断计划已制定,共 {} 步", len(plan.steps))
        return {"plan": plan.steps}

    return planner
