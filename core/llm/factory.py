"""LLM 클라이언트 팩토리."""

from __future__ import annotations

from core.config import Config
from core.exceptions import ConfigError
from core.llm.base import LLMClient
from core.llm.claude_client import ClaudeClient
from core.llm.llama_client import LlamaClient
from core.llm.openai_client import OpenAIClient


class LLMFactory:
    """설정 기반으로 LLM 클라이언트를 생성한다."""

    @staticmethod
    def create(provider: str, config: Config | None = None) -> LLMClient:
        """프로바이더 문자열로 클라이언트 인스턴스를 생성한다.

        Args:
            provider: 프로바이더 이름 ("claude", "openai", "llama").
            config: Config 인스턴스. None이면 새로 생성.

        Returns:
            LLMClient 구현체.

        Raises:
            ConfigError: 알 수 없는 프로바이더인 경우.
        """
        if config is None:
            config = Config()

        provider_cfg = config.get_provider_config(provider)

        match provider:
            case "claude":
                api_key = Config.get_api_key(provider_cfg["api_key_env"])
                return ClaudeClient(api_key=api_key, config=provider_cfg)  # type: ignore[return-value]
            case "openai":
                api_key = Config.get_api_key(provider_cfg["api_key_env"])
                return OpenAIClient(api_key=api_key, config=provider_cfg)  # type: ignore[return-value]
            case "llama":
                return LlamaClient(config=provider_cfg)  # type: ignore[return-value]
            case _:
                raise ConfigError(f"알 수 없는 프로바이더: {provider}")
