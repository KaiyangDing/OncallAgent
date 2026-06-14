"""诊断图的状态定义。"""

import operator
from typing import Annotated, TypedDict


class DiagnosisState(TypedDict):
    """Plan-Execute-Replan 诊断状态。

    字段:
    - task: 原始诊断任务描述
    - plan: 待执行的步骤列表(Replanner 会更新它)
    - past_steps: 已执行步骤及其结果,(步骤, 结果) 元组列表;追加式累积
    - report: 最终诊断报告(生成后即结束)
    """

    task: str
    plan: list[str]
    past_steps: Annotated[list[tuple[str, str]], operator.add]
    report: str


def format_past_steps(past_steps: list[tuple[str, str]]) -> str:
    """把已执行步骤格式化为可读文本(供 replanner、reporter 共用)。"""
    return "\n".join(
        f"{i}. {step}\n   结果:{result}" for i, (step, result) in enumerate(past_steps, 1)
    )
