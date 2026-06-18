"""请求中间件:为每个请求分配 request-id,贯穿日志链路。"""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from oncall_agent.context import request_id_var

REQUEST_ID_HEADER = "X-Request-ID"


async def request_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """为每个请求设置 request-id,并写入响应头。"""
    request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:8]
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        request_id_var.reset(token)
