"""M2 单测:索引服务的编排逻辑(用 mock 替身,不连真实资源)。"""

from unittest.mock import MagicMock

from oncall_agent.domain.knowledge.indexer import IndexingService
from oncall_agent.domain.knowledge.models import Chunk


def test_index_document_orchestration():
    """验证:切块 → 嵌入 → 先删后插 的调用顺序与参数。"""
    # 假分割器:返回两个固定块
    splitter = MagicMock()
    splitter.split.return_value = [
        Chunk(text="块一", source="a.md", title="T1", h1="H"),
        Chunk(text="块二", source="a.md", title="T2", h1="H"),
    ]
    # 假嵌入:返回两个假向量
    embedding = MagicMock()
    embedding.embed_texts.return_value = [[0.1, 0.2], [0.3, 0.4]]
    # 假存储
    store = MagicMock()

    service = IndexingService(splitter, embedding, store)
    count = service.index_document("原始内容", source="a.md")

    assert count == 2
    splitter.split.assert_called_once_with("原始内容", "a.md")
    embedding.embed_texts.assert_called_once_with(["块一", "块二"])
    store.delete_by_source.assert_called_once_with("a.md")
    store.insert.assert_called_once()


def test_index_empty_document_skips_storage():
    """空切分结果:不调用嵌入与存储,返回 0。"""
    splitter = MagicMock()
    splitter.split.return_value = []
    embedding = MagicMock()
    store = MagicMock()

    service = IndexingService(splitter, embedding, store)
    count = service.index_document("", source="empty.md")

    assert count == 0
    embedding.embed_texts.assert_not_called()
    store.insert.assert_not_called()
