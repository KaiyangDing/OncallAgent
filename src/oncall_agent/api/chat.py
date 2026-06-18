"""对话接口:非流式问答与流式问答(SSE)。"""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from oncall_agent.api.schemas import ApiResponse, ChatData, ChatRequest
from oncall_agent.dependencies import AppResources, get_resources
from oncall_agent.rate_limit import limiter
from oncall_agent.settings import get_settings

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ApiResponse[ChatData])
@limiter.limit(lambda: get_settings().rate_limit)
async def chat(
    request: Request,
    body: ChatRequest,
    resources: AppResources = Depends(get_resources),
) -> ApiResponse[ChatData]:
    """非流式对话:返回完整回答。"""
    answer = await resources.chat_service.chat(body.question, body.session_id)
    return ApiResponse.ok(ChatData(answer=answer))


@router.post("/stream")
@limiter.limit(lambda: get_settings().rate_limit)
async def chat_stream(
    request: Request,
    body: ChatRequest,
    resources: AppResources = Depends(get_resources),
) -> EventSourceResponse:
    """流式对话:以 SSE 逐块推送回答片段。"""

    async def event_generator() -> AsyncIterator[dict]:
        async for piece in resources.chat_service.chat_stream(body.question, body.session_id):
            yield {"event": "message", "data": piece}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
