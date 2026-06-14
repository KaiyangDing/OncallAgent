"""应用级依赖:在 lifespan 中装配,通过 FastAPI 依赖注入提供给路由。

所有有状态资源(向量库连接、索引服务等)在应用启动时构造一次,
存入 app.state,请求处理时按需取用,杜绝每请求重建。
"""

from dataclasses import dataclass

from fastapi import Request

from oncall_agent.domain.chat.service import ChatService
from oncall_agent.domain.diagnosis.service import DiagnosisService
from oncall_agent.domain.knowledge.indexer import IndexingService


@dataclass
class AppResources:
    """应用启动时装配、整个生命周期复用的资源集合。"""

    indexing_service: IndexingService
    chat_service: ChatService
    diagnosis_service: DiagnosisService


def get_resources(request: Request) -> AppResources:
    """FastAPI 依赖:从 app.state 取出已装配的资源。"""
    return request.app.state.resources
