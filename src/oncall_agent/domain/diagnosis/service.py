"""诊断服务:编译诊断图,以事件流驱动一次完整诊断。"""

from collections.abc import AsyncIterator

from langchain_core.tools import BaseTool
from langchain_qwq import ChatQwen

from oncall_agent.domain.diagnosis.graph import build_diagnosis_graph
from oncall_agent.domain.knowledge.retriever import RetrievalService

# 固定的诊断任务:自动巡检当前系统
_DIAGNOSIS_TASK = (
    "诊断当前系统是否存在告警。若存在,查询相关服务的指标与日志、"
    "检索运维知识库经验,分析根因并生成诊断报告。"
)


class DiagnosisService:
    """AIOps 自动诊断服务。"""

    def __init__(self, model: ChatQwen, tools: list[BaseTool], retrieval: RetrievalService) -> None:
        graph = build_diagnosis_graph(model, tools, retrieval)
        self._graph = graph.compile()

    async def diagnose(self) -> AsyncIterator[dict]:
        """运行一次诊断,产出过程事件(plan / step / report)。"""
        initial: dict = {"task": _DIAGNOSIS_TASK, "plan": [], "past_steps": [], "report": ""}

        async for chunk in self._graph.astream(initial, stream_mode="updates"):
            for node_name, update in chunk.items():
                event = self._to_event(node_name, update)
                if event is not None:
                    yield event

    @staticmethod
    def _to_event(node_name: str, update: dict) -> dict | None:
        """把某节点的状态更新转成对前端友好的事件。"""
        if node_name == "planner":
            return {"type": "plan", "steps": update.get("plan", [])}
        if node_name == "executor":
            past = update.get("past_steps") or []
            if past:
                step, result = past[-1]
                return {"type": "step", "step": step, "result": result}
        if node_name == "reporter":
            return {"type": "report", "report": update.get("report", "")}
        return None
