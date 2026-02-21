"""청킹 엔진 — 긴 문서의 Map-Reduce 처리."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from core.llm.base import LLMClient, LLMRequest, LLMResponse


@dataclass
class ChunkingConfig:
    """청킹 설정."""

    chunk_size_tokens: int = 4000
    context_threshold: float = 0.7
    map_model: str = "claude-haiku-4-5-20251001"
    reduce_model: str = "claude-sonnet-4-20250514"


# 의미 단위 분할 경계 패턴 (우선순위 순)
_SPLIT_PATTERNS = [
    re.compile(r"\n#{1,3}\s"),  # 마크다운 헤딩
    re.compile(r"\n\n"),  # 빈 줄 (문단 경계)
    re.compile(r"\n"),  # 줄바꿈
]


class ChunkingEngine:
    """긴 문서를 청크로 분할하고 Map-Reduce로 처리한다."""

    def __init__(self, client: LLMClient, config: ChunkingConfig | None = None) -> None:
        """
        Args:
            client: LLM 클라이언트 (토큰 카운팅 + 생성에 사용).
            config: 청킹 설정. None이면 기본값 사용.
        """
        self._client = client
        self._config = config or ChunkingConfig()

    def needs_chunking(self, content: str) -> bool:
        """
        컨텐츠가 청킹이 필요한지 판단한다.

        Args:
            content: 검사할 텍스트.

        Returns:
            토큰 수가 컨텍스트 threshold를 초과하면 True.
        """
        token_count = self._client.count_tokens(content)
        threshold = int(
            self._client.max_context_tokens * self._config.context_threshold
        )
        return token_count > threshold

    def split_chunks(self, content: str) -> list[str]:
        """
        컨텐츠를 chunk_size_tokens 단위로 분할한다.

        의미 단위 경계(헤딩, 문단, 줄바꿈)를 우선적으로 사용한다.

        Args:
            content: 분할할 텍스트.

        Returns:
            청크 리스트.
        """
        target_tokens = self._config.chunk_size_tokens
        if self._client.count_tokens(content) <= target_tokens:
            return [content]

        chunks: list[str] = []
        remaining = content

        while remaining:
            if self._client.count_tokens(remaining) <= target_tokens:
                chunks.append(remaining)
                break

            split_pos = self._find_split_position(remaining, target_tokens)
            chunks.append(remaining[:split_pos].rstrip())
            remaining = remaining[split_pos:].lstrip()

        return [c for c in chunks if c]

    def _find_split_position(self, text: str, target_tokens: int) -> int:
        """target_tokens 근처의 최적 분할 위치를 찾는다."""
        # 이진 탐색으로 target_tokens에 해당하는 대략적 문자 위치 찾기
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._client.count_tokens(text[:mid]) <= target_tokens:
                lo = mid + 1
            else:
                hi = mid
        char_limit = lo - 1 if lo > 0 else len(text)

        # 의미 단위 경계에서 분할 시도
        for pattern in _SPLIT_PATTERNS:
            # char_limit 이하에서 마지막 매치 찾기
            best_pos = -1
            for match in pattern.finditer(text):
                if match.start() <= char_limit and match.start() > 0:
                    best_pos = match.start()
                elif match.start() > char_limit:
                    break

            # 최소 10% 이상 채운 경계만 사용
            if best_pos > char_limit * 0.1:
                return best_pos

        # 공백 경계에서 분할 시도
        space_pos = text.rfind(" ", 0, char_limit)
        if space_pos > char_limit * 0.1:
            return space_pos

        # 경계를 못 찾으면 char_limit에서 강제 분할
        return max(char_limit, 1)

    async def map_reduce(
        self,
        content: str,
        map_prompt: str,
        reduce_prompt: str,
    ) -> LLMResponse:
        """
        Map-Reduce 파이프라인으로 긴 컨텐츠를 처리한다.

        1. 컨텐츠를 청크로 분할
        2. 각 청크를 map_model로 병렬 처리
        3. 결과들을 합쳐서 reduce_model로 최종 생성

        Args:
            content: 처리할 긴 텍스트.
            map_prompt: Map 단계 시스템 프롬프트.
            reduce_prompt: Reduce 단계 시스템 프롬프트.

        Returns:
            최종 LLMResponse.
        """
        chunks = self.split_chunks(content)

        # Map 단계 — 병렬 처리
        map_tasks = [
            self._client.generate(
                LLMRequest(
                    system_prompt=map_prompt,
                    user_prompt=chunk,
                    model=self._config.map_model,
                )
            )
            for chunk in chunks
        ]
        summaries = await asyncio.gather(*map_tasks)

        # Reduce 단계
        combined = "\n\n---\n\n".join(s.content for s in summaries)
        return await self._client.generate(
            LLMRequest(
                system_prompt=reduce_prompt,
                user_prompt=combined,
                model=self._config.reduce_model,
            )
        )
