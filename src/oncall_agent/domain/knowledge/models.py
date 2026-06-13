"""知识库领域模型。"""

from pydantic import BaseModel


class Chunk(BaseModel):
    """文档切块：一段文本 + 它的来源与章节信息。"""

    text: str
    source: str
    title: str = ""  # 所属章节标题(如 "CPU使用率过高 > 排查步骤"),可空
    h1: str = ""  # 一级标题,用于判断是否同属一个大章节
