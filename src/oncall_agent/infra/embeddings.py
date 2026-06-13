"""嵌入服务:调用 DashScope text-embedding 接口,将文本转为向量。

直接用 openai SDK 走 DashScope 的 OpenAI 兼容接口,不实现 LangChain
的 Embeddings 抽象——不依赖 langchain-milvus。
"""

from openai import OpenAI

from oncall_agent.settings import Settings


class EmbeddingService:
    """文本嵌入服务"""

    def __init__(self, settings: Settings):
        self._client = OpenAI(
            api_key=settings.dashscope_api_key.get_secret_value(),
            base_url=settings.dashscope_base_url,
        )
        self._model = settings.embedding_model
        self._dim = settings.embedding_dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入多段文本，返回等长的向量列表"""
        if not texts:
            return []

        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dim,
            encoding_format="float",
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        """嵌入单条查询文本，返回一个向量"""
        return self.embed_texts([text])[0]
