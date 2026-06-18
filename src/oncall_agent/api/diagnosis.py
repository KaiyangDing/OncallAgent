"""诊断接口:触发一次 AIOps 自动诊断,SSE 流式推送过程与报告。"""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from oncall_agent.dependencies import AppResources, get_resources
from oncall_agent.rate_limit import limiter
from oncall_agent.settings import get_settings

router = APIRouter(prefix="/api/diagnosis", tags=["diagnosis"])


@router.post("")
@limiter.limit(lambda: get_settings().rate_limit)
async def diagnose(
    request: Request,
    resources: AppResources = Depends(get_resources),
) -> EventSourceResponse:
    """触发自动诊断,以 SSE 推送 plan / step / report 事件。"""

    async def event_generator() -> AsyncIterator[dict]:
        async for event in resources.diagnosis_service.diagnose():
            yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
