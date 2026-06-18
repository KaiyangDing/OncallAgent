"""文档管理接口:上传并索引知识库文档。"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from oncall_agent.api.schemas import ApiResponse, DocumentIndexedData
from oncall_agent.dependencies import AppResources, get_resources

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_SUFFIXES = (".md", ".txt")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
_READ_CHUNK_SIZE = 64 * 1024  # 每次读取 64 KB


@router.post("", response_model=ApiResponse[DocumentIndexedData])
async def upload_document(
    file: UploadFile,
    resources: AppResources = Depends(get_resources),
) -> ApiResponse[DocumentIndexedData]:
    """上传一篇文档,切块、嵌入并写入向量库。"""
    filename = file.filename or ""
    if not filename.endswith(ALLOWED_SUFFIXES):
        raise HTTPException(
            status_code=400,
            detail=f"仅支持 {', '.join(ALLOWED_SUFFIXES)} 格式",
        )

    # 流式读取:边读边累计,超限立刻中断,避免大文件撑爆内存
    parts: list[bytes] = []
    total = 0
    while piece := await file.read(_READ_CHUNK_SIZE):
        total += len(piece)
        if total > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="文件超过 10 MB 限制")
        parts.append(piece)

    content = b"".join(parts).decode("utf-8")
    chunks = resources.indexing_service.index_document(content, source=filename)

    return ApiResponse.ok(DocumentIndexedData(source=filename, chunks=chunks))
