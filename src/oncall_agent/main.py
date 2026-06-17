"""FastAPI 应用入口。

采用应用工厂模式:create_app() 构造并配置 app。
所有资源初始化集中在 lifespan,模块 import 不产生副作用。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from oncall_agent.api import chat, diagnosis, documents, health
from oncall_agent.api.schemas import ApiResponse
from oncall_agent.dependencies import AppResources
from oncall_agent.domain.chat.service import ChatService
from oncall_agent.domain.chat.tools import make_knowledge_tool
from oncall_agent.domain.diagnosis.service import DiagnosisService
from oncall_agent.domain.knowledge.indexer import IndexingService
from oncall_agent.domain.knowledge.retriever import RetrievalService
from oncall_agent.domain.knowledge.splitter import DocumentSplitter
from oncall_agent.infra.embeddings import EmbeddingService
from oncall_agent.infra.llm import create_chat_model
from oncall_agent.infra.mcp import MCPToolProvider
from oncall_agent.infra.milvus import MilvusStore
from oncall_agent.logging import setup_logging
from oncall_agent.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期:启动时初始化资源,关闭时释放。"""
    settings: Settings = get_settings()
    setup_logging(settings)
    logger.info("{} v{} 启动中...", settings.app_name, settings.app_version)

    # 装配 infra 与 domain 组件
    embedding = EmbeddingService(settings)
    store = MilvusStore(settings)
    store.connect()
    splitter = DocumentSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        min_chunk_size=settings.min_chunk_size,
    )
    indexing_service = IndexingService(splitter, embedding, store)

    # 装配对话 Agent
    retrieval = RetrievalService(embedding, store, top_k=settings.retrieval_top_k)
    local_tools = [make_knowledge_tool(retrieval)]
    mcp_provider = MCPToolProvider(settings)
    mcp_tools = await mcp_provider.get_tools()
    chat_tools = local_tools + mcp_tools
    chat_model = create_chat_model(settings, streaming=True)
    checkpointer = MemorySaver()
    chat_service = ChatService(
        chat_model, chat_tools, checkpointer, max_history=settings.chat_max_history
    )

    # 装配诊断 Agent(复用同一套工具与检索;诊断不需要流式模型与会话记忆)
    diagnosis_model = create_chat_model(settings, streaming=False)
    diagnosis_service = DiagnosisService(diagnosis_model, chat_tools, retrieval)

    app.state.resources = AppResources(
        indexing_service=indexing_service,
        chat_service=chat_service,
        diagnosis_service=diagnosis_service,
    )
    logger.info("资源装配完成")

    yield

    store.close()
    logger.info("{} 已关闭", settings.app_name)


def create_app() -> FastAPI:
    """构造并配置 FastAPI 应用。"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(chat.router)
    app.include_router(diagnosis.router)

    # 挂载前端静态资源与首页
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse("static/index.html")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """客户端错误(主动抛出的 HTTPException)统一转为信封格式,保留原状态码。"""
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse.fail(str(exc.detail)).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """兜底异常处理:记录日志并返回统一的 500 响应。"""
        logger.exception("未处理异常: {} {}", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=ApiResponse.fail("服务器内部错误").model_dump(),
        )

    return app


# uvicorn 入口:oncall_agent.main:app
app = create_app()
