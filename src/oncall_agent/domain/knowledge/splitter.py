"""文档分割器:将 Markdown 文档切成适合检索的语义块。

三阶段策略:
1. 按 Markdown 标题分割,保留章节结构(标题进入元数据)
2. 对超长块按字符递归切分
3. 合并过小的块(合并时保留章节标题,修正旧实现丢元数据的缺陷)
"""

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from oncall_agent.domain.knowledge.models import Chunk


class DocumentSplitter:
    """Markdown 文档分割器"""

    def __init__(
        self, chunk_size: int = 800, chunk_overlap: int = 100, min_chunk_size: int = 300
    ) -> None:
        self._min_chunk_size = min_chunk_size
        self._header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2")],
            strip_headers=False,
        )
        self._char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(self, content: str, source: str) -> list[Chunk]:
        """将文档内容切成 Chunk 列表。"""
        if not content.strip():
            return []

        # 阶段一:按标题分割,得到带 h1/h2 元数据的段落
        header_docs = self._header_splitter.split_text(content)

        # 阶段二:对每段按字符长度进一步切分
        split_docs = self._char_splitter.split_documents(header_docs)

        # 转成我们的 Chunk(从元数据提取章节标题)
        chunks = [
            Chunk(
                text=doc.page_content,
                source=source,
                title=self._make_title(doc.metadata),
                h1=doc.metadata.get("h1", ""),
            )
            for doc in split_docs
        ]

        # 阶段三:合并过小的相邻块
        return self._merge_small(chunks)

    def _make_title(self, metadata: dict) -> str:
        """从标题元数据拼出层级标题,如 'CPU过高 > 排查步骤'。"""
        parts = [metadata[key] for key in ("h1", "h2") if metadata.get(key)]
        return " > ".join(parts)

    def _merge_small(self, chunks: list[Chunk]) -> list[Chunk]:
        """将过小的块并入前一块,仅当二者 h1 相同(同属一个大章节)。"""
        if not chunks:
            return []

        merged: list[Chunk] = [chunks[0]]
        for chunk in chunks[1:]:
            prev = merged[-1]
            if len(chunk.text) < self._min_chunk_size and chunk.h1 == prev.h1:
                merged[-1] = Chunk(
                    text=prev.text + "\n\n" + chunk.text,
                    source=prev.source,
                    title=prev.title,
                    h1=prev.h1,
                )
            else:
                merged.append(chunk)
        return merged
