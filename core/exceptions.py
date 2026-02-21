"""커스텀 예외 계층."""


class WhiBlogError(Exception):
    """whi-blog 기본 예외."""


class ConfigError(WhiBlogError):
    """설정 관련 에러."""


class LLMError(WhiBlogError):
    """LLM 호출 에러."""


class LLMRateLimitError(LLMError):
    """LLM API Rate Limit 초과."""


class LLMAuthError(LLMError):
    """LLM API 인증 실패."""


class LLMContextOverflowError(LLMError):
    """Map-Reduce 후에도 컨텍스트 초과."""


class SourceError(WhiBlogError):
    """소스 파싱/크롤링 에러."""


class PublishError(WhiBlogError):
    """게시 파이프라인 에러."""
