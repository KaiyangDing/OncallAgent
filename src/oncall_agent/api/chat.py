"""对话接口:非流式问答与流式问答(SSE)。"""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from oncall_agent.api.schemas import ApiResponse, ChatData, ChatRequest
from oncall_agent.dependencies import AppResources, get_resources

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ApiResponse[ChatData])
async def chat(
    request: ChatRequest,
    resources: AppResources = Depends(get_resources),
) -> ApiResponse[ChatData]:
    """非流式对话:返回完整回答。"""
    answer = await resources.chat_service.chat(request.question, request.session_id)
    return ApiResponse.ok(ChatData(answer=answer))


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    resources: AppResources = Depends(get_resources),
) -> EventSourceResponse:
    """流式对话:以 SSE 逐块推送回答片段。"""

    async def event_generator() -> AsyncIterator[dict]:
        async for piece in resources.chat_service.chat_stream(request.question, request.session_id):
            yield {"event": "message", "data": piece}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
