"""检索服务测试:相似度阈值过滤。"""

from unittest.mock import MagicMock

from oncall_agent.domain.knowledge.retriever import RetrievalService


def _service(hits: list[dict], threshold: float = 0.5) -> RetrievalService:
    """构造一个用假 store/embedding 的 RetrievalService。"""
    embedding = MagicMock()
    embedding.embed_query.return_value = [0.1, 0.2]
    store = MagicMock()
    store.search.return_value = hits
    return RetrievalService(embedding, store, top_k=3, score_threshold=threshold)


def test_keeps_results_above_threshold():
    """分数达标的结果被保留。"""
    service = _service(
        [
            {"text": "CPU 排查方案", "source": "cpu.md", "score": 0.65},
            {"text": "磁盘方案", "source": "disk.md", "score": 0.55},
        ]
    )
    result = service.retrieve("CPU 高")
    assert "CPU 排查方案" in result
    assert "cpu.md" in result


def test_filters_out_low_score_results():
    """所有结果都低于阈值时,返回"没有相关内容"。"""
    service = _service(
        [
            {"text": "无关内容", "source": "x.md", "score": 0.21},
            {"text": "也无关", "source": "y.md", "score": 0.19},
        ]
    )
    result = service.retrieve("今天天气")
    assert "没有找到相关内容" in result
    assert "无关内容" not in result


def test_partial_filter():
    """只保留达标的,滤掉不达标的。"""
    service = _service(
        [
            {"text": "相关", "source": "a.md", "score": 0.6},
            {"text": "不相关", "source": "b.md", "score": 0.3},
        ]
    )
    result = service.retrieve("查询")
    assert "相关" in result
    assert "不相关" not in result
