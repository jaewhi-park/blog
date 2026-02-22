"""글 작성 파이프라인 오케스트레이터."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.content.image_manager import ImageInfo, ImageManager
from core.content.markdown_generator import MarkdownGenerator, PostMetadata
from core.content.reference_manager import ReferenceManager
from core.content.template_manager import TemplateManager
from core.llm.base import LLMClient, LLMRequest
from core.llm.chunking import ChunkingEngine
from core.llm.factory import LLMFactory
from core.sources.aggregator import SourceAggregator, SourceInput

_SYSTEM_PROMPT_AUTO = (
    "당신은 기술 블로그 글을 작성하는 전문 작가입니다. "
    "주어진 주제에 대해 한국어로 기술 블로그 게시글을 작성하세요. "
    "영어 수학/기술 용어는 그대로 유지하세요. "
    "마크다운 형식으로 작성하되, front matter는 포함하지 마세요. "
    "수식은 $...$ (인라인) 또는 $$...$$ (블록) 형식을 사용하세요."
)

_SYSTEM_PROMPT_FEEDBACK = (
    "당신은 기술 블로그 글 작성을 돕는 편집자입니다. "
    "사용자의 초안을 읽고 구조, 논리, 명확성, 기술적 정확성 측면에서 "
    "개선 피드백을 한국어로 제공하세요. 영어 수학/기술 용어는 그대로 유지하세요."
)

_MAP_PROMPT = (
    "다음 텍스트 청크의 핵심 내용을 요약하세요. "
    "중요한 기술적 세부사항과 수식은 유지하세요."
)

_REDUCE_PROMPT = (
    "다음 요약들을 종합하여 하나의 기술 블로그 게시글을 작성하세요. "
    "한국어로 작성하되, 영어 수학/기술 용어는 그대로 유지하세요. "
    "마크다운 형식으로 작성하되, front matter는 포함하지 마세요."
)


@dataclass
class WriteRequest:
    """글 작성 요청."""

    mode: str  # "direct", "pair", "auto"
    content: str | None = None
    sources: list[SourceInput] | None = None
    template_id: str | None = None
    reference_id: str | None = None
    provider: str | None = None
    model: str | None = None
    category_path: str = ""
    tags: list[str] = field(default_factory=list)
    title: str = ""
    prompt: str = ""


@dataclass
class WriteResult:
    """글 작성 결과."""

    content: str
    metadata: PostMetadata
    images: list[ImageInfo] = field(default_factory=list)
    image_data: dict[str, bytes] = field(default_factory=dict)
    llm_usage: dict | None = None


class ContentPipeline:
    """글 작성 파이프라인 — 소스 처리, LLM 호출, 후처리를 통합한다."""

    def __init__(
        self,
        llm_factory: LLMFactory,
        source_aggregator: SourceAggregator,
        chunking_engine: ChunkingEngine | None = None,
        markdown_generator: MarkdownGenerator | None = None,
        image_manager: ImageManager | None = None,
        template_manager: TemplateManager | None = None,
        reference_manager: ReferenceManager | None = None,
    ) -> None:
        """
        Args:
            llm_factory: LLM 클라이언트 팩토리.
            source_aggregator: 소스 어그리게이터.
            chunking_engine: 청킹 엔진 (None이면 Map-Reduce 미사용).
            markdown_generator: 마크다운 생성기 (None이면 기본값 사용).
            image_manager: 이미지 매니저 (None이면 이미지 처리 생략).
            template_manager: 템플릿 매니저 (None이면 템플릿 미사용).
            reference_manager: 레퍼런스 매니저 (None이면 레퍼런스 미사용).
        """
        self._llm_factory = llm_factory
        self._aggregator = source_aggregator
        self._chunking = chunking_engine
        self._md_gen = markdown_generator or MarkdownGenerator()
        self._image_mgr = image_manager
        self._tpl_mgr = template_manager
        self._ref_mgr = reference_manager

    async def execute(self, request: WriteRequest) -> WriteResult:
        """
        글 작성 파이프라인을 실행한다.

        1. 소스 처리 (자동 생성인 경우)
        2. LLM 호출 (토큰 카운팅 → 직접 호출 or Map-Reduce)
        3. 후처리 (PostMetadata 생성)

        Args:
            request: 글 작성 요청.

        Returns:
            생성된 컨텐츠, 메타데이터, 이미지 정보.
        """
        if request.mode == "direct":
            return self._build_direct_result(request)

        client = self._llm_factory.create(request.provider or "claude")

        # 소스 처리
        source_text = ""
        images: list[ImageInfo] = []
        image_data: dict[str, bytes] = {}

        if request.sources:
            aggregated = await self._aggregator.aggregate(request.sources)
            source_text = aggregated.combined_text
            images = aggregated.images
            image_data = aggregated.image_data

        # 템플릿 렌더링
        resolved = self._resolve_template(request, source_text)

        if resolved:
            system_prompt, user_prompt = resolved
        else:
            system_prompt = _SYSTEM_PROMPT_AUTO
            user_prompt = self._build_user_prompt(request, source_text)

        # LLM 호출
        content, usage = await self._generate(
            client,
            user_prompt,
            request.model,
            system_prompt=system_prompt,
        )

        metadata = self._build_metadata(request)

        return WriteResult(
            content=content,
            metadata=metadata,
            images=images,
            image_data=image_data,
            llm_usage=usage,
        )

    async def get_feedback(self, request: WriteRequest) -> WriteResult:
        """
        페어 라이팅: 초안에 대한 LLM 피드백을 반환한다.

        Args:
            request: 초안이 포함된 글 작성 요청.

        Returns:
            피드백 내용이 담긴 WriteResult.
        """
        client = self._llm_factory.create(request.provider or "claude")

        # 템플릿이 있으면 system_prompt에 스타일 컨텍스트 추가
        system_prompt = _SYSTEM_PROMPT_FEEDBACK
        if request.template_id and self._tpl_mgr:
            tpl = self._tpl_mgr.get(request.template_id)
            style_context = f"\n\n## 원하는 글 스타일\n\n{tpl.system_prompt}"
            system_prompt = _SYSTEM_PROMPT_FEEDBACK + style_context

        llm_request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=f"다음 초안에 대한 피드백을 제공해주세요:\n\n{request.content}",
            model=request.model,
        )
        response = await client.generate(llm_request)

        metadata = self._build_metadata(request)

        return WriteResult(
            content=response.content,
            metadata=metadata,
            llm_usage=response.usage,
        )

    def _build_direct_result(self, request: WriteRequest) -> WriteResult:
        """직접 작성 모드 결과를 생성한다."""
        metadata = self._build_metadata(request)
        return WriteResult(
            content=request.content or "",
            metadata=metadata,
        )

    def _build_user_prompt(self, request: WriteRequest, source_text: str) -> str:
        """LLM에 전달할 user prompt를 구성한다."""
        parts: list[str] = []

        if source_text:
            parts.append(f"다음 소스 자료를 참고하여 글을 작성하세요:\n\n{source_text}")

        if request.content:
            parts.append(f"초안:\n\n{request.content}")

        if request.prompt:
            parts.append(f"지시사항: {request.prompt}")
        elif request.title:
            parts.append(f"주제: {request.title}")

        return "\n\n---\n\n".join(parts) if parts else request.title

    def _resolve_template(
        self, request: WriteRequest, source_text: str
    ) -> tuple[str, str] | None:
        """템플릿과 레퍼런스를 해석하여 (system_prompt, user_prompt)를 반환한다.

        template_id가 없거나 template_manager가 없으면 None을 반환한다.
        템플릿 사용 시 sources는 별도 ``{sources}`` 섹션으로 전달하므로,
        content에는 소스를 포함하지 않는다 (중복 방지).
        """
        if not request.template_id or not self._tpl_mgr:
            return None

        # 스타일 레퍼런스 텍스트 획득
        style_reference = ""
        if request.reference_id and self._ref_mgr:
            style_reference = self._ref_mgr.get_content(request.reference_id)

        # content에는 소스를 제외 (템플릿이 {sources}로 별도 배치)
        content = self._build_user_prompt(request, source_text="")

        return self._tpl_mgr.render(
            request.template_id,
            content=content,
            sources=source_text,
            style_reference=style_reference,
        )

    async def _generate(
        self,
        client: LLMClient,
        user_prompt: str,
        model: str | None,
        system_prompt: str = _SYSTEM_PROMPT_AUTO,
    ) -> tuple[str, dict]:
        """토큰 카운팅 기반으로 직접 호출 또는 Map-Reduce를 수행한다."""
        # Map-Reduce 분기
        if self._chunking and self._chunking.needs_chunking(user_prompt):
            response = await self._chunking.map_reduce(
                content=user_prompt,
                map_prompt=_MAP_PROMPT,
                reduce_prompt=_REDUCE_PROMPT,
            )
            return response.content, response.usage

        # 직접 호출
        llm_request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
        )
        response = await client.generate(llm_request)
        return response.content, response.usage

    def _build_metadata(self, request: WriteRequest) -> PostMetadata:
        """요청에서 PostMetadata를 생성한다."""
        return PostMetadata(
            title=request.title,
            categories=[request.category_path] if request.category_path else [],
            tags=request.tags,
            llm_assisted=request.mode == "pair",
            llm_generated=request.mode == "auto",
            llm_model=request.model,
        )
