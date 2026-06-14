"""诊断图:Plan-Execute-Replan 编排。

planner → executor → replanner ──plan 非空──→ executor(循环)
                               └─plan 为空──→ reporter → END
"""

from langchain_core.tools import BaseTool
from langchain_qwq import ChatQwen
from langgraph.graph import END, START, StateGraph

from oncall_agent.domain.diagnosis.executor import make_executor
from oncall_agent.domain.diagnosis.planner import make_planner
from oncall_agent.domain.diagnosis.replanner import make_replanner
from oncall_agent.domain.diagnosis.reporter import make_reporter
from oncall_agent.domain.diagnosis.state import DiagnosisState
from oncall_agent.domain.knowledge.retriever import RetrievalService


def build_diagnosis_graph(model: ChatQwen, tools: list[BaseTool], retrieval: RetrievalService):
    """构造诊断图(未编译)。"""

    def route_after_replan(state: DiagnosisState) -> str:
        """plan 为空 → 生成报告;否则继续执行。"""
        return "reporter" if not state["plan"] else "executor"

    graph = StateGraph(DiagnosisState)
    graph.add_node("planner", make_planner(model, tools, retrieval))
    graph.add_node("executor", make_executor(model, tools))
    graph.add_node("replanner", make_replanner(model))
    graph.add_node("reporter", make_reporter(model))

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "replanner")
    graph.add_conditional_edges("replanner", route_after_replan, ["executor", "reporter"])
    graph.add_edge("reporter", END)

    return graph
