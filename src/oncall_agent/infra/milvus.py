"""Milvus 向量库封装。

直接使用 pymilvus 的 MilvusClient(2.4+ 新式 API),自管 collection 的
建表、插入、检索、按来源删除。不依赖 langchain-milvus。
"""

from pymilvus import DataType, MilvusClient

from oncall_agent.settings import Settings


class MilvusStore:
    """知识库向量存储：一个collection管理所有文件块"""

    # 字段名常量，避免散落的字符串字面量
    FIELD_ID = "id"
    FIELD_VECTOR = "vector"
    FIELD_TEXT = "text"
    FIELD_SOURCE = "source"

    TEXT_MAX_LENGTH = 8000
    SOURCE_MAX_LENGTH = 512

    def __init__(self, settings: Settings) -> None:
        self._uri = f"http://{settings.milvus_host}:{settings.milvus_port}"
        self._collection = settings.milvus_collection
        self._dim = settings.embedding_dim
        self._client: MilvusClient | None = None

    def connect(self) -> None:
        """建立连接并确保 collection 就绪（幂等）"""
        self._client = MilvusClient(uri=self._uri)
        if not self._client.has_collection(self._collection):
            self._create_collection()

    @property
    def client(self) -> MilvusClient:
        """返回已连接的客户端，未连接则报错"""
        if self._client is None:
            raise RuntimeError("MilvusStore 未连接,请先调用 connect()")
        return self._client

    def _create_collection(self) -> None:
        """创建 collection:定义 schema、建向量索引、加载到内存。"""
        schema = MilvusClient.create_schema(auto_id=False)
        schema.add_field(self.FIELD_ID, DataType.VARCHAR, is_primary=True, max_length=64)
        schema.add_field(self.FIELD_VECTOR, DataType.FLOAT_VECTOR, dim=self._dim)
        schema.add_field(self.FIELD_TEXT, DataType.VARCHAR, max_length=self.TEXT_MAX_LENGTH)
        schema.add_field(self.FIELD_SOURCE, DataType.VARCHAR, max_length=self.SOURCE_MAX_LENGTH)

        index_params = MilvusClient.prepare_index_params()
        index_params.add_index(
            field_name=self.FIELD_VECTOR,
            index_type="IVF_FLAT",
            metric_type="COSINE",
            params={"nlist": 128},
        )

        self.client.create_collection(
            collection_name=self._collection,
            schema=schema,
            index_params=index_params,
        )

    def insert(
        self, ids: list[str], vectors: list[list[float]], texts: list[str], sources: list[str]
    ) -> None:
        """插入一批文档块（id 已存在则覆盖）"""
        rows = [
            {
                self.FIELD_ID: id_,
                self.FIELD_VECTOR: vector,
                self.FIELD_TEXT: text,
                self.FIELD_SOURCE: source,
            }
            for id_, vector, text, source in zip(ids, vectors, texts, sources, strict=True)
        ]
        self.client.upsert(collection_name=self._collection, data=rows)
        self.client.flush(self._collection)

    def search(self, query_vector: list[float], top_k: int) -> list[dict]:
        """向量相似度检索,返回 top_k 个最相近的块。

        返回每项含 text、source、score(余弦相似度,越大越相近)。
        """
        results = self.client.search(
            collection_name=self._collection,
            data=[query_vector],
            limit=top_k,
            output_fields=[self.FIELD_TEXT, self.FIELD_SOURCE],
        )
        hits = results[0]
        return [
            {
                "text": hit["entity"][self.FIELD_TEXT],
                "source": hit["entity"][self.FIELD_SOURCE],
                "score": hit["distance"],
            }
            for hit in hits
        ]

    def delete_by_source(self, source: str) -> None:
        """删除某个来源文件的所有块(用于重新索引前清理旧数据)。"""
        self.client.delete(
            collection_name=self._collection,
            filter=f'{self.FIELD_SOURCE} == "{source}"',
        )
        self.client.flush(self._collection)

    def close(self) -> None:
        """关闭连接。"""
        if self._client is not None:
            self._client.close()
            self._client = None
