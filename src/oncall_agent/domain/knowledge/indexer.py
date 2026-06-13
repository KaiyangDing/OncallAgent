"""索引服务:将文档切块、嵌入并写入向量库。

组装 DocumentSplitter + EmbeddingService + MilvusStore 三个组件,
对外提供「索引一篇文档」的能力。组件由外部注入,本类不直接读配置。
"""

import hashlib

from loguru import logger

from oncall_agent.domain.knowledge.splitter import DocumentSplitter
from oncall_agent.infra.embeddings import EmbeddingService
from oncall_agent.infra.milvus import MilvusStore


class IndexingService:
    """文档索引服务。"""

    def __init__(
        self, splitter: DocumentSplitter, embedding: EmbeddingService, store: MilvusStore
    ) -> None:
        self._splitter = splitter
        self._embedding = embedding
        self._store = store

    def index_document(self, content: str, source: str) -> int:
        """索引一篇文档,返回写入的块数。

        若该 source 已存在,先删除旧块再写入,实现覆盖更新。
        """

        chunks = self._splitter.split(content, source)
        if not chunks:
            logger.warning("文档 {} 切分结果为空,跳过", source)
            return 0

        vectors = self._embedding.embed_texts([c.text for c in chunks])

        # 覆盖更新:先清掉该来源的旧数据
        self._store.delete_by_source(source)
        self._store.insert(
            ids=[self._chunk_id(source, i) for i in range(len(chunks))],
            vectors=vectors,
            texts=[c.text for c in chunks],
            sources=[c.source for c in chunks],
        )

        logger.info("索引完成:{} → {} 块", source, len(chunks))
        return len(chunks)

    @staticmethod
    def _chunk_id(source: str, index: int) -> str:
        """生成稳定且唯一的块 ID:source 的哈希 + 序号。"""
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]
        return f"{digest}-{index}"
