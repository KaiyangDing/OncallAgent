"""Reporter 节点:综合所有执行结果,生成最终诊断报告。"""

from collections.abc import Awaitable, Callable

from langchain_qwq import ChatQwen
from loguru import logger

from oncall_agent.domain.diagnosis.prompts import REPORTER_PROMPT
from oncall_agent.domain.diagnosis.state import DiagnosisState, format_past_steps

NodeFn = Callable[[DiagnosisState], Awaitable[dict]]


def make_reporter(model: ChatQwen) -> NodeFn:
    """工厂:返回绑定了模型的 reporter 节点。"""
    report_chain = REPORTER_PROMPT | model

    async def reporter(state: DiagnosisState) -> dict:
        """基于全部已执行步骤生成 Markdown 诊断报告。"""
        report_msg = await report_chain.ainvoke(
            {
                "task": state["task"],
                "past_steps": format_past_steps(state["past_steps"]),
            }
        )
        logger.info("诊断报告已生成,长度 {}", len(report_msg.content))
        return {"report": report_msg.content}

    return reporter
