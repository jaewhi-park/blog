"""Config 단위 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from core.config import Config
from core.exceptions import ConfigError


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    """임시 설정 디렉토리를 생성한다."""
    llm_cfg = {
        "providers": {
            "claude": {
                "default_model": "claude-sonnet-4-20250514",
                "api_key_env": "ANTHROPIC_API_KEY",  # pragma: allowlist secret
                "models": [
                    {"id": "claude-sonnet-4-20250514", "max_context_tokens": 200000},
                ],
            },
            "openai": {
                "default_model": "gpt-4o",
                "api_key_env": "OPENAI_API_KEY",  # pragma: allowlist secret
                "models": [
                    {"id": "gpt-4o", "max_context_tokens": 128000},
                ],
            },
            "llama": {
                "default_model": "llama3.1",
                "endpoint": "http://localhost:11434",
                "models": [
                    {"id": "llama3.1", "max_context_tokens": 128000},
                ],
            },
        },
        "chunking": {
            "chunk_size_tokens": 4000,
            "context_threshold": 0.7,
        },
    }
    (tmp_path / "llm_config.yaml").write_text(yaml.dump(llm_cfg), encoding="utf-8")
    return tmp_path


class TestConfig:
    """Config 클래스 테스트."""

    def test_load_llm_config(self, config_dir: Path) -> None:
        cfg = Config(config_dir=config_dir)
        assert "providers" in cfg.llm
        assert "claude" in cfg.llm["providers"]

    def test_get_provider_config(self, config_dir: Path) -> None:
        cfg = Config(config_dir=config_dir)
        provider_cfg = cfg.get_provider_config("claude")
        assert provider_cfg["default_model"] == "claude-sonnet-4-20250514"

    def test_get_provider_config_unknown_raises(self, config_dir: Path) -> None:
        cfg = Config(config_dir=config_dir)
        with pytest.raises(ConfigError, match="프로바이더 설정을 찾을 수 없습니다"):
            cfg.get_provider_config("unknown")

    def test_get_api_key_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_API_KEY", "sk-test-123")
        assert Config.get_api_key("TEST_API_KEY") == "sk-test-123"

    def test_get_api_key_missing_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MISSING_KEY", raising=False)
        with pytest.raises(ConfigError, match="API 키가 설정되지 않았습니다"):
            Config.get_api_key("MISSING_KEY")

    def test_get_chunking_config(self, config_dir: Path) -> None:
        cfg = Config(config_dir=config_dir)
        chunking = cfg.get_chunking_config()
        assert chunking["chunk_size_tokens"] == 4000

    def test_missing_yaml_returns_empty(self, tmp_path: Path) -> None:
        cfg = Config(config_dir=tmp_path)
        assert cfg.llm == {}
        assert cfg.arxiv == {}

    def test_empty_yaml_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "llm_config.yaml").write_text("", encoding="utf-8")
        cfg = Config(config_dir=tmp_path)
        assert cfg.llm == {}
