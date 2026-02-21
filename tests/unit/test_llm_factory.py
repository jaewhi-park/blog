"""LLMFactory 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from core.config import Config
from core.exceptions import ConfigError
from core.llm.claude_client import ClaudeClient
from core.llm.factory import LLMFactory
from core.llm.llama_client import LlamaClient
from core.llm.openai_client import OpenAIClient


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    """LLM 설정이 포함된 임시 디렉토리."""
    llm_cfg = {
        "providers": {
            "claude": {
                "default_model": "claude-sonnet-4-20250514",
                "api_key_env": "ANTHROPIC_API_KEY",  # pragma: allowlist secret
                "models": [],
            },
            "openai": {
                "default_model": "gpt-4o",
                "api_key_env": "OPENAI_API_KEY",  # pragma: allowlist secret
                "models": [],
            },
            "llama": {
                "default_model": "llama3.1",
                "endpoint": "http://localhost:11434",
                "models": [],
            },
        },
    }
    (tmp_path / "llm_config.yaml").write_text(yaml.dump(llm_cfg), encoding="utf-8")
    return tmp_path


class TestLLMFactory:
    """LLMFactory 테스트."""

    def test_create_claude(
        self, config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        config = Config(config_dir=config_dir)
        client = LLMFactory.create("claude", config=config)
        assert isinstance(client, ClaudeClient)
        assert client.provider_name == "claude"

    def test_create_openai(
        self, config_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        config = Config(config_dir=config_dir)
        client = LLMFactory.create("openai", config=config)
        assert isinstance(client, OpenAIClient)
        assert client.provider_name == "openai"

    def test_create_llama(self, config_dir: Path) -> None:
        config = Config(config_dir=config_dir)
        client = LLMFactory.create("llama", config=config)
        assert isinstance(client, LlamaClient)
        assert client.provider_name == "llama"

    def test_create_unknown_raises(self, config_dir: Path) -> None:
        config = Config(config_dir=config_dir)
        with pytest.raises(ConfigError):
            LLMFactory.create("unknown", config=config)
