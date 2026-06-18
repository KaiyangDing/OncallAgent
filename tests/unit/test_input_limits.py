"""输入边界测试:超长文本与超大文件被正确拒绝。"""

import pytest
from pydantic import ValidationError

from oncall_agent.api.schemas import ChatRequest


def test_question_length_limit():
    """超长 question 被 Pydantic 校验拒绝。"""
    # 正常长度通过
    ChatRequest(session_id="s1", question="正常问题")

    # 超过 4000 字符被拒
    try:
        ChatRequest(session_id="s1", question="x" * 4001)
        raise AssertionError("超长 question 应被拒绝")
    except ValidationError:
        pass


def test_empty_question_rejected():
    """空 question 被拒绝。"""
    try:
        ChatRequest(session_id="s1", question="")
        raise AssertionError("空 question 应被拒绝")
    except ValidationError:
        pass


def test_whitespace_only_question_rejected():
    """纯空格 question 被拒绝(strip 后为空)。"""
    with pytest.raises(ValidationError):
        ChatRequest(session_id="s1", question="   ")
