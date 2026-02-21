"""전역 설정 관리자."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from core.exceptions import ConfigError

# 프로젝트 루트 (core/ 의 부모 디렉토리)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# load_dotenv는 모듈 로드 시 1회만 실행
load_dotenv()


class Config:
    """YAML 설정 파일과 환경변수를 통합 관리한다."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """
        Args:
            config_dir: 설정 파일 디렉토리 경로. None이면 프로젝트 루트의 config/.
        """
        self._config_dir = config_dir or (_PROJECT_ROOT / "config")
        self.llm: dict[str, Any] = self._load_yaml("llm_config.yaml")
        self.arxiv: dict[str, Any] = self._load_yaml("arxiv_digest.yaml")
        self.disclaimer: dict[str, Any] = self._load_yaml("disclaimer.yaml")

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        """YAML 파일을 로드한다.

        Raises:
            ConfigError: YAML 파싱에 실패한 경우.
        """
        path = self._config_dir / filename
        if not path.exists():
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"YAML 파싱 실패 ({filename}): {e}") from e

    @staticmethod
    def get_api_key(env_var: str) -> str:
        """환경변수에서 API 키를 가져온다.

        우선순위:
            1. os.environ (export된 환경변수)
            2. .env 파일 (python-dotenv로 로드됨)
            3. 미발견 → ConfigError 발생

        Args:
            env_var: 환경변수 이름 (예: "ANTHROPIC_API_KEY").

        Returns:
            API 키 문자열.

        Raises:
            ConfigError: 환경변수가 설정되지 않았거나 빈 문자열인 경우.
        """
        value = os.environ.get(env_var, "").strip()
        if not value:
            raise ConfigError(
                f"API 키가 설정되지 않았습니다: {env_var}\n"
                f".env 파일에 {env_var}=... 을 추가하거나 환경변수로 설정하세요."
            )
        return value

    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """프로바이더 설정을 반환한다.

        Args:
            provider: 프로바이더 이름 ("claude", "openai", "llama").

        Returns:
            프로바이더 설정 dict.

        Raises:
            ConfigError: 프로바이더 설정이 없는 경우.
        """
        providers = self.llm.get("providers", {})
        if provider not in providers:
            raise ConfigError(f"프로바이더 설정을 찾을 수 없습니다: {provider}")
        return providers[provider]

    def get_chunking_config(self) -> dict[str, Any]:
        """청킹 설정을 반환한다."""
        return self.llm.get("chunking", {})
