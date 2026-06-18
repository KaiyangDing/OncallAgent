"""知识检索服务:把向量检索包装成对 Agent 友好的文本结果。"""

from oncall_agent.infra.embeddings import EmbeddingService
from oncall_agent.infra.milvus import MilvusStore


class RetrievalService:
    """知识库检索:查询 → 向量 → Milvus 召回 → 格式化文本。"""

    def __init__(
        self,
        embedding: EmbeddingService,
        store: MilvusStore,
        top_k: int = 3,
        score_threshold: float = 0.5,
    ) -> None:
        self._embedding = embedding
        self._store = store
        self._top_k = top_k
        self._score_threshold = score_threshold

    def retrieve(self, query: str) -> str:
        """检索并返回拼接好的参考文本(供 LLM 阅读)。"""
        query_vector = self._embedding.embed_query(query)
        hits = self._store.search(query_vector, top_k=self._top_k)

        # 过滤掉相似度低于阈值的结果,避免无关内容误导 LLM
        relevant = [h for h in hits if h["score"] >= self._score_threshold]
        if not relevant:
            return "知识库中没有找到相关内容。"

        blocks = []
        for i, hit in enumerate(relevant, 1):
            blocks.append(f"【参考资料 {i}|来源:{hit['source']}】\n{hit['text']}")
        return "\n\n".join(blocks)
