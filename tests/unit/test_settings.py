"""配置校验测试:缺失 / 空 API key 必须在构造时 fail fast。"""

import pytest
from pydantic import ValidationError

from oncall_agent.settings import Settings


def test_empty_api_key_is_rejected(monkeypatch: pytest.MonkeyPatch):
    """空字符串 key 应触发校验错误(防住 .env 里留空值的手误)。"""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")
    with pytest.raises(ValidationError, match="DASHSCOPE_API_KEY"):
        Settings(_env_file=None)


def test_missing_api_key_is_rejected(monkeypatch: pytest.MonkeyPatch):
    """完全缺失 key 也应触发校验错误。"""
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_valid_api_key_passes(monkeypatch: pytest.MonkeyPatch):
    """提供有效 key 时正常构造。"""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-key")
    settings = Settings(_env_file=None)
    assert settings.dashscope_api_key.get_secret_value() == "sk-test-key"
