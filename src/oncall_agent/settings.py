"""应用配置:从环境变量 / .env 加载,启动时完成类型校验。

所有可调参数集中在此,杜绝散落在代码各处的魔法数字。
"""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。字段名小写,环境变量不区分大小写。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用
    app_name: str = "OnCall Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 9900

    # DashScope(通义千问)
    # dashscope_api_key: SecretStr  # 必填方案
    dashscope_api_key: SecretStr = Field(default=SecretStr(""))
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    chat_model: str = "qwen-max"
    embedding_model: str = "text-embedding-v4"
    embedding_dim: int = 1024

    # Milvus 向量库
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "knowledge"

    # 会话持久化(SQLite checkpointer)
    checkpoint_db: str = "data/checkpoints.db"

    # 文档分割
    chunk_size: int = 800
    chunk_overlap: int = 100
    min_chunk_size: int = 300

    # RAG 检索
    retrieval_top_k: int = 3
    chat_max_history: int = 20
    retrieval_score_threshold: float = 0.5

    # MCP 服务器(键为服务器名,值为 streamable-http 端点)
    mcp_monitor_url: str = "http://127.0.0.1:8001/mcp"
    mcp_logs_url: str = "http://127.0.0.1:8002/mcp"

    # 限流(按 IP,每分钟最大请求数)
    rate_limit: str = "10/minute"

    # 校验器方案
    @field_validator("dashscope_api_key")
    @classmethod
    def _require_api_key(cls, v: SecretStr) -> SecretStr:
        """启动时校验:API key 必须非空,否则拒绝启动并明确报错。"""
        if not v.get_secret_value().strip():
            raise ValueError(
                "DASHSCOPE_API_KEY 未设置。请在 .env 文件中填入有效的 API key "
                "(可参考 .env.example)。"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """返回全局唯一配置实例(带缓存,全程只构造一次)。"""
    return Settings()
