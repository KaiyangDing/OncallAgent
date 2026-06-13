"""M2 单测:文档分割器。"""

from oncall_agent.domain.knowledge.splitter import DocumentSplitter


def test_split_empty_returns_nothing():
    """空内容切出空列表。"""
    splitter = DocumentSplitter()
    assert splitter.split("   ", source="x.md") == []


def test_split_extracts_title_and_source():
    """切块带上来源与章节标题。"""
    content = "# 一级标题\n\n这是正文内容,描述一些情况。\n\n## 子章节\n\n子章节的具体内容在这里。"
    splitter = DocumentSplitter()

    chunks = splitter.split(content, source="doc.md")

    assert len(chunks) >= 1
    assert all(c.source == "doc.md" for c in chunks)
    assert all(c.h1 == "一级标题" for c in chunks)
    # 至少有一块的 title 包含一级标题
    assert any("一级标题" in c.title for c in chunks)


def test_small_chunk_merged_within_same_h1():
    """同一 h1 下的过小块会被合并。"""
    # min_chunk_size=300,制造一个很短的 h2 段落,应被并入前一块
    content = "# 大章节\n\n" + "正" * 400 + "\n\n## 小节\n\n短文本。"
    splitter = DocumentSplitter(min_chunk_size=300)

    chunks = splitter.split(content, source="doc.md")

    # "短文本"那段不足 300 字且 h1 相同,应被合并,不单独成块
    assert all("短文本" not in c.text or len(c.text) > 50 for c in chunks)