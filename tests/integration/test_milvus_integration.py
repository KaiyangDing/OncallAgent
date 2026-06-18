"""Milvus 集成测试:真连本地 Milvus,验证存取链路与相似度排序。

需要本地 Milvus 在线(docker compose up -d)。
运行:uv run pytest -m integration
"""

import pytest

from oncall_agent.infra.milvus import MilvusStore
from oncall_agent.settings import Settings

pytestmark = pytest.mark.integration


@pytest.fixture
def store():
    """提供一个连到独立测试 collection 的 MilvusStore,测试后清理。"""
    settings = Settings(
        dashscope_api_key="sk-test",  # 集成测试不调 DashScope,占位即可
        milvus_collection="test_integration_knowledge",
        embedding_dim=4,  # 用小维度,测试里手造向量方便
    )
    s = MilvusStore(settings)
    s.connect()
    # 清掉可能残留的旧测试数据,保证干净起点
    s.client.drop_collection(s._collection)
    s.connect()  # 重建干净的 collection

    yield s  # 把 store 交给测试使用

    # teardown:删除测试 collection,不留痕迹
    s.client.drop_collection(s._collection)
    s.close()


def test_insert_and_search_returns_nearest(store: MilvusStore):
    """插入三个向量,检索时最相近的排在最前。"""
    # 手造 4 维向量:doc-a 和查询向量方向最一致
    store.insert(
        ids=["doc-a", "doc-b", "doc-c"],
        vectors=[[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]],
        texts=["关于 A 的内容", "关于 B 的内容", "关于 C 的内容"],
        sources=["a.md", "b.md", "c.md"],
    )

    # 查询向量和 doc-a 方向一致 → doc-a 应排第一
    results = store.search([0.9, 0.1, 0.0, 0.0], top_k=3)

    assert len(results) == 3
    assert results[0]["text"] == "关于 A 的内容"  # 最相近的排最前
    assert results[0]["source"] == "a.md"
    # COSINE 相似度:越相近分数越高,第一个应 >= 第二个
    assert results[0]["score"] >= results[1]["score"]


def test_delete_by_source_removes_only_that_source(store: MilvusStore):
    """按来源删除,只删该来源的块。"""
    store.insert(
        ids=["x-1", "y-1"],
        vectors=[[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
        texts=["来自 x", "来自 y"],
        sources=["x.md", "y.md"],
    )

    store.delete_by_source("x.md")

    # 检索全部,x.md 的应已被删,只剩 y.md
    results = store.search([0.0, 1.0, 0.0, 0.0], top_k=10)
    sources = {r["source"] for r in results}
    assert "x.md" not in sources
    assert "y.md" in sources
