# TRD: whi-blog — Technical Reference Document

## 1. 개요

본 문서는 whi-blog의 기술 설계를 상세히 기술한다. PRD에서 정의한 기능 요구사항을 구현하기 위한 아키텍처, 인터페이스, 데이터 모델, 모듈 간 상호작용을 명세한다.

### 1.1 기술 스택 상세

| 영역 | 기술 | 버전/비고 |
|------|------|----------|
| 정적 사이트 | Hugo | Extended version (SCSS 지원) |
| 테마 | hugo-book | git submodule |
| 호스팅 | GitHub Pages | github.io 도메인 (추후 커스텀 도메인) |
| CI/CD | GitHub Actions | deploy.yml, auto-post.yml |
| CMS UI | Streamlit | >= 1.30 |
| LLM - Claude | anthropic SDK | Python |
| LLM - OpenAI | openai SDK | Python |
| LLM - Llama | ollama REST API | 로컬 http://localhost:11434 |
| PDF 파싱 | PyMuPDF (fitz) | 텍스트 + 이미지 추출 |
| 웹 크롤링 | httpx + BeautifulSoup4 | 비동기 지원 |
| arxiv | arxiv Python 패키지 | API 클라이언트 |
| 경제 데이터 | fredapi, yfinance | FRED API, Yahoo Finance |
| 비동기 처리 | asyncio | Map-Reduce 병렬 |
| 설정 관리 | PyYAML, python-dotenv | YAML + .env |
| Git 연동 | GitPython | 커밋, 브랜치, PR |
| GitHub API | PyGithub | PR 생성 |
| 테스트 | pytest, pytest-asyncio | 유닛 + 통합 |
| 코드 품질 | ruff, mypy | 린트 + 타입 체크 |
| 보안 | detect-secrets | pre-commit hook |

### 1.2 Python 버전

Python 3.11+ (match 문, TaskGroup 등 활용)

---

## 2. 코어 모듈 설계

### 2.1 LLM 클라이언트 (`core/llm/`)

#### 2.1.1 LLMClient Protocol (`core/llm/base.py`)

모든 LLM 프로바이더가 구현해야 하는 인터페이스.

```python
from typing import Protocol, AsyncIterator
from dataclasses import dataclass

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict  # {"input_tokens": int, "output_tokens": int}

@dataclass
class LLMRequest:
    system_prompt: str
    user_prompt: str
    model: str | None = None          # None이면 프로바이더 기본 모델 사용
    temperature: float = 0.7
    max_tokens: int = 4096

class LLMClient(Protocol):
    """LLM 프로바이더 통합 인터페이스"""

    @property
    def provider_name(self) -> str: ...

    @property
    def max_context_tokens(self) -> int: ...

    @property
    def available_models(self) -> list[dict]: ...

    async def generate(self, request: LLMRequest) -> LLMResponse: ...

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]: ...

    def count_tokens(self, text: str) -> int: ...
```

#### 2.1.2 프로바이더 구현

각 프로바이더는 LLMClient를 구현한다.

**ClaudeClient** (`core/llm/claude_client.py`)
```python
class ClaudeClient:
    def __init__(self, config: ProviderConfig):
        self._client = anthropic.AsyncAnthropic(api_key=config.api_key)
        self._config = config

    async def generate(self, request: LLMRequest) -> LLMResponse: ...
    def count_tokens(self, text: str) -> int:
        # anthropic.count_tokens() 사용
```

**OpenAIClient** (`core/llm/openai_client.py`)
```python
class OpenAIClient:
    def __init__(self, config: ProviderConfig):
        self._client = openai.AsyncOpenAI(api_key=config.api_key)
        self._config = config

    async def generate(self, request: LLMRequest) -> LLMResponse: ...
    def count_tokens(self, text: str) -> int:
        # tiktoken 사용
```

**LlamaClient** (`core/llm/llama_client.py`)
```python
class LlamaClient:
    def __init__(self, config: ProviderConfig):
        self._endpoint = config.endpoint  # http://localhost:11434
        self._config = config

    async def generate(self, request: LLMRequest) -> LLMResponse: ...
    def count_tokens(self, text: str) -> int:
        # 근사치: len(text) // 4
```

#### 2.1.3 LLM 팩토리 (`core/llm/factory.py`)

설정 기반으로 클라이언트를 생성하는 팩토리.

```python
class LLMFactory:
    @staticmethod
    def create(provider: str, config: ProviderConfig) -> LLMClient:
        match provider:
            case "claude":
                return ClaudeClient(config)
            case "openai":
                return OpenAIClient(config)
            case "llama":
                return LlamaClient(config)
            case _:
                raise ValueError(f"Unknown provider: {provider}")
```

#### 2.1.4 청킹 엔진 (`core/llm/chunking.py`)

긴 문서의 Map-Reduce 처리를 담당한다.

```python
@dataclass
class ChunkingConfig:
    chunk_size_tokens: int = 4000
    context_threshold: float = 0.7     # 컨텍스트의 70% 초과 시 청킹
    map_model: str = "claude-haiku"
    reduce_model: str = "claude-sonnet"

class ChunkingEngine:
    def __init__(self, client: LLMClient, config: ChunkingConfig): ...

    def needs_chunking(self, content: str) -> bool:
        """토큰 수가 컨텍스트 threshold를 초과하는지 판단"""
        token_count = self._client.count_tokens(content)
        return token_count > self._client.max_context_tokens * self._config.context_threshold

    def split_chunks(self, content: str) -> list[str]:
        """content를 chunk_size_tokens 단위로 분할"""

    async def map_reduce(
        self,
        content: str,
        map_prompt: str,
        reduce_prompt: str,
    ) -> str:
        """
        1. content를 청크로 분할
        2. 각 청크를 map_model로 병렬 요약 (asyncio.gather)
        3. 요약들을 합쳐서 reduce_model로 최종 생성
        """
        chunks = self.split_chunks(content)

        # Map 단계 — 병렬 처리
        map_tasks = [
            self._client.generate(LLMRequest(
                system_prompt=map_prompt,
                user_prompt=chunk,
                model=self._config.map_model,
            ))
            for chunk in chunks
        ]
        summaries = await asyncio.gather(*map_tasks)

        # Reduce 단계
        combined = "\n\n---\n\n".join(s.content for s in summaries)
        result = await self._client.generate(LLMRequest(
            system_prompt=reduce_prompt,
            user_prompt=combined,
            model=self._config.reduce_model,
        ))
        return result.content
```

---

### 2.2 컨텐츠 관리 (`core/content/`)

#### 2.2.1 마크다운 생성기 (`core/content/markdown_generator.py`)

Hugo 호환 마크다운 파일을 생성한다.

```python
@dataclass
class PostMetadata:
    title: str
    date: str                          # ISO 8601
    categories: list[str]              # ["math", "probability"]
    tags: list[str]
    draft: bool = False
    math: bool = True                  # KaTeX 활성화
    llm_generated: bool = False        # LLM 자동 생성 여부
    llm_assisted: bool = False         # LLM 페어 라이팅 여부
    llm_disclaimer: bool = False       # 면책 조항 표시 여부
    llm_model: str | None = None       # 사용된 LLM 모델
    sources: list[str] | None = None   # 참고 소스 목록

class MarkdownGenerator:
    def generate(self, metadata: PostMetadata, content: str) -> str:
        """front matter + content 마크다운 문자열 생성"""

    def save(self, metadata: PostMetadata, content: str, base_path: Path) -> Path:
        """
        Hugo content 디렉토리에 파일 저장
        경로: hugo-site/content/{category_path}/{slug}.md
        """
```

**생성되는 마크다운 예시:**
```markdown
---
title: "Random Matrix Theory와 Free Probability의 연결"
date: 2025-02-21T09:00:00+09:00
categories: ["math", "probability"]
tags: ["random-matrix", "free-probability"]
math: true
llm_disclaimer: true
llm_model: "claude-sonnet-4-20250514"
---

{{< disclaimer >}}

## 1. 서론

Wigner의 반원 법칙은...
```

#### 2.2.2 카테고리 매니저 (`core/content/category_manager.py`)

Hugo의 디렉토리 기반 계층형 카테고리를 관리한다.

```python
@dataclass
class Category:
    name: str
    slug: str
    children: list["Category"]
    parent: str | None = None

class CategoryManager:
    def __init__(self, hugo_content_path: Path): ...

    def list_all(self) -> list[Category]:
        """현재 카테고리 트리 반환"""

    def add(self, name: str, parent_path: str | None = None) -> Category:
        """
        카테고리 추가
        - hugo-site/content/{parent_path}/{slug}/ 디렉토리 생성
        - _index.md 생성 (카테고리 메타 정보)
        """

    def remove(self, category_path: str) -> bool:
        """카테고리 삭제 (하위 게시글이 없는 경우만)"""

    def move(self, category_path: str, new_parent_path: str) -> bool:
        """카테고리 이동 (재구조화)"""
```

**Hugo 카테고리 디렉토리 구조:**
```
hugo-site/content/
├── math/
│   ├── _index.md                  # weight: 1, title: "Mathematics"
│   ├── probability/
│   │   ├── _index.md              # weight: 1, title: "Probability"
│   │   ├── random-matrix-theory/
│   │   │   ├── _index.md          # weight: 1, title: "Random Matrix Theory"
│   │   │   └── wigner-semicircle.md
│   │   └── free-probability-intro.md
│   └── algebra/
│       ├── _index.md
│       └── linear-algebra-basics.md
├── investment/
│   ├── _index.md
│   └── macro-analysis/
│       ├── _index.md
│       └── fred-q1-report.md
└── ai/
    ├── _index.md
    └── ml-engineering/
        └── _index.md
```

#### 2.2.3 이미지 매니저 (`core/content/image_manager.py`)

```python
@dataclass
class ImageInfo:
    filename: str
    source: str              # "upload", "pdf_extract"
    page: int | None = None  # PDF 추출 시 원본 페이지
    caption: str | None = None

class ImageManager:
    def __init__(self, hugo_static_path: Path): ...

    def save_image(self, image_data: bytes, post_slug: str, filename: str) -> str:
        """
        이미지를 Hugo static에 저장하고 마크다운 참조 경로 반환
        저장: hugo-site/static/images/{post_slug}/{filename}
        반환: "/images/{post_slug}/{filename}"
        """

    def extract_from_pdf(self, pdf_path: Path, page_range: tuple | None) -> list[ImageInfo]:
        """PDF에서 이미지 추출 (PyMuPDF 사용)"""

    def generate_markdown_ref(self, image_info: ImageInfo) -> str:
        """![caption](/images/post-slug/filename.png) 형태 반환"""
```

#### 2.2.4 템플릿 매니저 (`core/content/template_manager.py`)

```python
@dataclass
class PromptTemplate:
    id: str                    # 파일명 기반 (예: "lecture_note")
    name: str                  # 표시명 (예: "렉쳐노트")
    description: str
    system_prompt: str
    user_prompt_template: str  # {content}, {sources} 등 플레이스홀더 포함
    created_at: str
    updated_at: str

class TemplateManager:
    def __init__(self, templates_dir: Path): ...

    def list_all(self) -> list[PromptTemplate]: ...
    def get(self, template_id: str) -> PromptTemplate: ...
    def create(self, template: PromptTemplate) -> PromptTemplate: ...
    def update(self, template_id: str, template: PromptTemplate) -> PromptTemplate: ...
    def delete(self, template_id: str) -> bool: ...

    def render(self, template_id: str, content: str, **kwargs) -> tuple[str, str]:
        """
        (system_prompt, rendered_user_prompt) 반환
        user_prompt_template의 플레이스홀더를 치환
        """
```

**템플릿 YAML 스키마:**
```yaml
# templates/lecture_note.yaml
id: "lecture_note"
name: "렉쳐노트"
description: "수학 렉쳐노트 스타일로 작성"
system_prompt: |
  You are a mathematics educator writing lecture notes.
  Use rigorous notation, include proofs where appropriate,
  and provide intuitive explanations alongside formal definitions.
  Write in Korean with English mathematical terms.
user_prompt_template: |
  다음 내용을 바탕으로 렉쳐노트를 작성해주세요.

  {content}

  {style_reference}
created_at: "2025-02-21T00:00:00+09:00"
updated_at: "2025-02-21T00:00:00+09:00"
```

#### 2.2.5 스타일 레퍼런스 매니저 (`core/content/reference_manager.py`)

```python
@dataclass
class StyleReference:
    id: str
    name: str                  # 표시명 (예: "Terence Tao 블로그 스타일")
    source_type: str           # "file" | "url"
    source_path: str           # 파일 경로 또는 URL
    content_cache: str | None  # URL의 경우 크롤링 결과 캐시
    file_type: str | None      # "pdf", "md", "txt" (파일인 경우)
    created_at: str
    updated_at: str

class ReferenceManager:
    def __init__(self, references_dir: Path): ...

    def list_all(self) -> list[StyleReference]: ...
    def add_file(self, name: str, file_path: Path) -> StyleReference: ...
    def add_url(self, name: str, url: str) -> StyleReference: ...
    def remove(self, ref_id: str) -> bool: ...
    def get_content(self, ref_id: str) -> str:
        """레퍼런스 텍스트 내용 반환 (URL은 캐시에서, 파일은 직접 읽기)"""
```

**레퍼런스 메타데이터 저장:**
```yaml
# references/index.yaml
references:
  - id: "tao_blog_style"
    name: "Terence Tao 블로그 스타일"
    source_type: "url"
    source_path: "https://terrytao.wordpress.com/example-post"
    file_type: null
    created_at: "2025-02-21T00:00:00+09:00"
  - id: "my_lecture_format"
    name: "내 렉쳐노트 포맷"
    source_type: "file"
    source_path: "my_lecture_format.md"
    file_type: "md"
    created_at: "2025-02-21T00:00:00+09:00"
```

---

### 2.3 소스 처리 (`core/sources/`)

#### 2.3.1 PDF 파서 (`core/sources/pdf_parser.py`)

```python
@dataclass
class PDFContent:
    text: str
    images: list[ImageInfo]
    total_pages: int
    extracted_range: tuple[int, int] | None  # (start_page, end_page)

class PDFParser:
    def parse(
        self,
        pdf_path: Path,
        page_range: tuple[int, int] | None = None,
        extract_images: bool = True,
    ) -> PDFContent:
        """
        PyMuPDF로 PDF 파싱
        - page_range: (start, end) 1-indexed, inclusive
        - extract_images: 이미지 추출 여부
        """
```

#### 2.3.2 URL 크롤러 (`core/sources/url_crawler.py`)

```python
@dataclass
class CrawledContent:
    url: str
    title: str
    text: str
    fetched_at: str

class URLCrawler:
    async def crawl(self, url: str) -> CrawledContent:
        """
        httpx + BeautifulSoup4로 웹 페이지 크롤링
        - HTML에서 본문 텍스트 추출
        - 불필요한 요소(nav, footer, ads) 제거
        """
```

#### 2.3.3 arxiv 클라이언트 (`core/sources/arxiv_client.py`)

```python
@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published: str
    pdf_url: str
    url: str

class ArxivClient:
    async def fetch_recent(
        self,
        categories: list[str],
        max_results: int = 50,
    ) -> list[ArxivPaper]:
        """카테고리별 최신 논문 조회"""

    async def fetch_by_id(self, arxiv_id: str) -> ArxivPaper:
        """특정 논문 조회"""

    async def download_pdf(self, arxiv_id: str, save_path: Path) -> Path:
        """PDF 다운로드"""
```

#### 2.3.4 소스 어그리게이터 (`core/sources/aggregator.py`)

복수 소스를 병합하는 모듈.

```python
@dataclass
class SourceInput:
    source_type: str           # "pdf", "url", "arxiv"
    path_or_url: str
    page_range: tuple[int, int] | None = None  # PDF 전용
    label: str | None = None   # 소스 구분용 라벨

@dataclass
class AggregatedContent:
    combined_text: str
    sources: list[SourceInput]
    images: list[ImageInfo]
    total_tokens_estimate: int

class SourceAggregator:
    def __init__(
        self,
        pdf_parser: PDFParser,
        url_crawler: URLCrawler,
        arxiv_client: ArxivClient,
    ): ...

    async def aggregate(self, sources: list[SourceInput]) -> AggregatedContent:
        """
        복수 소스를 파싱/크롤링하여 하나의 AggregatedContent로 병합
        각 소스 텍스트는 구분자로 분리하여 LLM이 출처를 구분할 수 있게 함
        """
```

**병합 텍스트 포맷:**
```
=== Source 1: paper_A.pdf (pages 1-15) ===
[텍스트 내용]

=== Source 2: paper_B.pdf (pages 3-8) ===
[텍스트 내용]

=== Source 3: https://arxiv.org/abs/2501.12345 ===
[텍스트 내용]
```

---

### 2.4 데이터 Fetcher (`core/fetchers/`)

#### 2.4.1 DataFetcher Protocol (`core/fetchers/base.py`)

```python
from typing import Protocol, Any

class DataFetcher(Protocol):
    @property
    def name(self) -> str: ...

    async def fetch(self, **kwargs) -> dict[str, Any]:
        """
        데이터 fetch 후 dict 반환
        반환값에는 'data' (원본 데이터)와 'summary' (텍스트 요약) 포함
        """
        ...

    def format_for_llm(self, data: dict[str, Any]) -> str:
        """LLM 프롬프트에 삽입할 수 있는 텍스트 형태로 변환"""
        ...
```

#### 2.4.2 구현체

**FREDFetcher** (`core/fetchers/fred_fetcher.py`)
```python
class FREDFetcher:
    def __init__(self):
        self._client = Fred(api_key=os.getenv("FRED_API_KEY"))

    async def fetch(
        self,
        series_ids: list[str],       # 예: ["GDP", "UNRATE", "CPIAUCSL"]
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]: ...

    def format_for_llm(self, data: dict[str, Any]) -> str:
        """시계열 데이터를 텍스트 테이블 + 기술 통계로 변환"""
```

**YFinanceFetcher** (`core/fetchers/yfinance_fetcher.py`)
```python
class YFinanceFetcher:
    async def fetch(
        self,
        tickers: list[str],          # 예: ["SPY", "QQQ", "TLT"]
        period: str = "1mo",
    ) -> dict[str, Any]: ...

    def format_for_llm(self, data: dict[str, Any]) -> str:
        """주가 데이터를 요약 텍스트로 변환"""
```

**ArxivFetcher** (`core/fetchers/arxiv_fetcher.py`)
```python
class ArxivFetcher:
    async def fetch(
        self,
        query: str,
        max_results: int = 10,
    ) -> dict[str, Any]: ...

    def format_for_llm(self, data: dict[str, Any]) -> str:
        """논문 리스트를 제목 + abstract 텍스트로 변환"""
```

---

### 2.5 게시 파이프라인 (`core/publishing/`)

#### 2.5.1 Git 매니저 (`core/publishing/git_manager.py`)

```python
class GitManager:
    def __init__(self, repo_path: Path): ...

    def commit_and_push(self, message: str, files: list[Path]) -> str:
        """파일 추가 → 커밋 → push, 커밋 SHA 반환"""

    def create_branch(self, branch_name: str) -> str:
        """새 브랜치 생성"""

    def create_pr(
        self,
        title: str,
        body: str,
        branch: str,
        base: str = "main",
    ) -> str:
        """
        GitHub PR 생성 (PyGithub 사용)
        PR URL 반환
        """
```

#### 2.5.2 Hugo 빌더 (`core/publishing/hugo_builder.py`)

```python
class HugoBuilder:
    def __init__(self, hugo_site_path: Path): ...

    def build(self) -> bool:
        """hugo build 실행"""

    def serve(self, port: int = 1313) -> subprocess.Popen:
        """hugo server -D 실행 (로컬 미리보기)"""

    def get_preview_url(self, post_path: Path) -> str:
        """게시글의 로컬 미리보기 URL 반환"""
```

---

### 2.6 스케줄러 (`core/scheduler/`)

#### 2.6.1 arxiv 다이제스트 (`core/scheduler/arxiv_digest.py`)

GitHub Actions에서 실행되는 스크립트.

```python
@dataclass
class DigestConfig:
    categories: list[str]
    keywords: list[str]
    interest_description: str
    max_papers: int
    seen_papers_path: Path

class ArxivDigest:
    def __init__(
        self,
        config: DigestConfig,
        arxiv_client: ArxivClient,
        llm_client: LLMClient,
        git_manager: GitManager,
    ): ...

    async def run(self) -> str | None:
        """
        전체 다이제스트 파이프라인 실행
        1. fetch_papers — arxiv에서 최신 논문 가져오기
        2. filter_seen — 이미 처리한 논문 제외
        3. keyword_filter — 키워드 기반 1차 필터
        4. llm_filter — LLM 기반 2차 필터 (관심사 매칭)
        5. generate_digest — 선별 논문 요약 마크다운 생성
        6. create_pr — PR 생성
        반환: PR URL 또는 None (관심 논문 없는 경우)
        """

    def _load_seen(self) -> set[str]: ...
    def _save_seen(self, seen: set[str]) -> None: ...

    def _keyword_filter(self, papers: list[ArxivPaper]) -> list[ArxivPaper]:
        """키워드 매칭 (비용 0)"""

    async def _llm_filter(self, papers: list[ArxivPaper]) -> list[ArxivPaper]:
        """LLM에 abstract 전달하여 관심도 판별"""
```

**LLM 필터링 프롬프트 설계:**
```
System: You are a research paper relevance classifier.

User: Given the following research interest description:
"{interest_description}"

Rate the relevance of each paper (1-5) and respond in JSON:
[
  {"arxiv_id": "...", "relevance": 4, "reason": "..."},
  ...
]

Papers:
1. [{title}] {abstract}
2. ...
```

#### 2.6.2 자동 포스팅 (`core/scheduler/auto_post.py`)

```python
class AutoPost:
    def __init__(
        self,
        fetchers: dict[str, DataFetcher],
        llm_client: LLMClient,
        template_manager: TemplateManager,
        markdown_generator: MarkdownGenerator,
        git_manager: GitManager,
    ): ...

    async def run(self, job_config: dict) -> str | None:
        """
        사전 정의된 자동 포스팅 Job 실행
        1. fetcher로 데이터 수집
        2. 템플릿 적용 + LLM 리포트 생성
        3. 마크다운 저장
        4. PR 생성
        """
```

---

## 3. 설정 관리

### 3.1 설정 로더 (`core/config.py`)

```python
class Config:
    """전역 설정 관리자"""

    def __init__(self, config_dir: Path = Path("config")):
        self.llm = self._load_yaml("llm_config.yaml")
        self.arxiv = self._load_yaml("arxiv_digest.yaml")
        self.disclaimer = self._load_yaml("disclaimer.yaml")

    @staticmethod
    def get_api_key(env_var: str) -> str:
        """
        환경변수 → .env fallback → 미발견 시 에러
        우선순위:
        1. os.environ[env_var]
        2. dotenv에서 로드
        3. ConfigError 발생
        """
```

### 3.2 설정 파일 목록

```
config/
├── llm_config.yaml       # LLM 프로바이더, 모델, 청킹 설정
├── arxiv_digest.yaml     # arxiv 관심사, 카테고리, 스케줄
├── disclaimer.yaml       # LLM 면책 조항 문구 및 스타일
└── site_config.yaml      # 블로그 일반 설정 (이름, 설명, URL 등)
```

### 3.3 환경 변수

```bash
# .env.example
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
FRED_API_KEY=
GITHUB_TOKEN=           # PR 생성용
HUGO_SITE_PATH=./hugo-site
```

---

## 4. Streamlit UI 설계 (`ui/`)

### 4.1 페이지 구조

```
ui/
├── app.py                  # 메인 앱, 사이드바 네비게이션
├── pages/
│   ├── 01_write.py         # 글 작성 (직접/페어/자동)
│   ├── 02_categories.py    # 카테고리 관리
│   ├── 03_templates.py     # 템플릿 관리
│   ├── 04_references.py    # 스타일 레퍼런스 관리
│   ├── 05_reports.py       # 외부 데이터 리포트
│   └── 06_settings.py      # 관심사, LLM 설정, 면책 조항
└── components/
    ├── editor.py           # 마크다운 에디터 컴포넌트
    ├── preview.py          # 미리보기 컴포넌트 (수식 렌더링)
    ├── source_input.py     # 소스 입력 컴포넌트 (복수 소스)
    ├── llm_selector.py     # 프로바이더/모델 선택 컴포넌트
    └── image_picker.py     # 이미지 선택 컴포넌트
```

### 4.2 글 작성 페이지 (`pages/01_write.py`) 워크플로우

```
┌─────────────────────────────────────────────┐
│  글 작성 모드 선택                             │
│  [직접 작성] [페어 라이팅] [자동 생성]            │
├─────────────────────────────────────────────┤
│                                             │
│  카테고리 선택: [math > probability > ...]    │
│  태그 입력: [...]                             │
│                                             │
│  ─── 직접 작성 모드 ───                       │
│  [마크다운 에디터]          [실시간 미리보기]    │
│                                             │
│  ─── 페어 라이팅 모드 ───                     │
│  [마크다운 에디터]          [실시간 미리보기]    │
│  프로바이더: [Claude ▾]  모델: [Sonnet ▾]     │
│  템플릿: [렉쳐노트 ▾]  (optional)             │
│  레퍼런스: [Tao 블로그 스타일 ▾]  (optional)   │
│  [LLM 피드백 요청] → [피드백 표시] → [반영]    │
│                                             │
│  ─── 자동 생성 모드 ───                       │
│  소스 추가:                                   │
│    [+ PDF] [+ URL] [+ arxiv]                │
│    ├── paper.pdf (pages 1-15)    [✕]        │
│    └── https://arxiv.org/...     [✕]        │
│  프로바이더: [Claude ▾]  모델: [Sonnet ▾]     │
│  템플릿: [Summary ▾]  (optional)             │
│  레퍼런스: [선택안함 ▾]  (optional)            │
│  [생성 요청] → [초안 표시] → [편집] → [게시]   │
│                                             │
├─────────────────────────────────────────────┤
│  이미지: [업로드] [PDF에서 선택]               │
│                                             │
│  [임시저장]  [미리보기 (Hugo)]  [게시하기]      │
└─────────────────────────────────────────────┘
```

### 4.3 설정 페이지 (`pages/06_settings.py`)

```
┌─────────────────────────────────────────────┐
│  ═══ LLM 설정 ═══                            │
│  기본 프로바이더: [Claude ▾]                   │
│  기본 모델: [Sonnet ▾]                        │
│  Map 모델: [Haiku ▾]                         │
│  Reduce 모델: [Sonnet ▾]                     │
│                                             │
│  ═══ arxiv 관심사 ═══                        │
│  카테고리:                                    │
│    [math.PR] [✕]  [math.SP] [✕]  [+ 추가]   │
│  키워드:                                      │
│    [random matrix] [✕]  [free probability]   │
│    [✕]  [+ 추가]                             │
│  관심사 설명:                                  │
│    [텍스트 에디터]                              │
│                                             │
│  ═══ 면책 조항 ═══                            │
│  LLM 생성 면책: [✓] 활성화                    │
│    문구: [텍스트 입력]                         │
│    스타일: [warning ▾]                        │
│  LLM 보조 면책: [✓] 활성화                    │
│    문구: [텍스트 입력]                         │
│                                             │
│  [저장]                                      │
└─────────────────────────────────────────────┘
```

---

## 5. Hugo 사이트 설계

### 5.1 Hugo 설정 (`hugo-site/config.toml`)

```toml
baseURL = "https://username.github.io/whi-blog/"
languageCode = "ko"
title = "whi-blog"
theme = "hugo-book"

[params]
  BookTheme = "auto"
  BookToC = true
  BookComments = true

[params.giscus]
  repo = "username/whi-blog"
  repoId = ""
  category = "Comments"
  categoryId = ""
  mapping = "pathname"
  reactionsEnabled = "1"
  emitMetadata = "0"
  theme = "preferred_color_scheme"

[markup.goldmark.renderer]
  unsafe = true

[markup.goldmark.extensions.passthrough]
  enable = true

[markup.goldmark.extensions.passthrough.delimiters]
  block = [["\\[", "\\]"], ["$$", "$$"]]
  inline = [["\\(", "\\)"], ["$", "$"]]
```

### 5.2 면책 조항 Shortcode (`hugo-site/layouts/shortcodes/disclaimer.html`)

```html
{{ $disclaimer := .Page.Params.llm_disclaimer }}
{{ if $disclaimer }}
  {{ $config := site.Data.disclaimer }}
  {{ if .Page.Params.llm_generated }}
    <div class="disclaimer disclaimer-{{ $config.llm_generated.style }}">
      {{ $config.llm_generated.text }}
    </div>
  {{ else if .Page.Params.llm_assisted }}
    <div class="disclaimer disclaimer-{{ $config.llm_assisted.style }}">
      {{ $config.llm_assisted.text }}
    </div>
  {{ end }}
{{ end }}
```

### 5.3 KaTeX 설정

Hugo Book 테마는 KaTeX를 기본 지원한다. `config.toml`의 passthrough 설정으로 `$...$`, `$$...$$` 구문을 활성화한다.

---

## 6. GitHub Actions 설계

### 6.1 배포 워크플로우 (`.github/workflows/deploy.yml`)

```yaml
name: Deploy Hugo

on:
  push:
    branches: [main]
    paths: ["hugo-site/**"]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true    # Hugo Book 테마

      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: "latest"
          extended: true

      - name: Build
        working-directory: hugo-site
        run: hugo --minify

      - name: Deploy
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: hugo-site/public
```

### 6.2 자동 포스팅 워크플로우 (`.github/workflows/auto-post.yml`)

```yaml
name: Auto Post

on:
  schedule:
    - cron: "0 0 * * *"     # 매일 UTC 00:00 (KST 09:00)
  workflow_dispatch:          # 수동 트리거 가능

jobs:
  arxiv-digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run arxiv digest
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python -m scripts.run_arxiv_digest

      - name: Run scheduled auto posts
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python -m scripts.run_auto_posts
```

---

## 7. 글 작성 파이프라인 통합 (`core/pipeline.py`)

모든 글 작성 모드의 핵심 파이프라인을 통합하는 오케스트레이터.

```python
@dataclass
class WriteRequest:
    mode: str                                  # "direct", "pair", "auto"
    content: str | None = None                 # 직접 작성/페어 라이팅 초안
    sources: list[SourceInput] | None = None   # 자동 생성 소스
    template_id: str | None = None
    reference_id: str | None = None
    provider: str | None = None
    model: str | None = None
    category_path: str = ""
    tags: list[str] = field(default_factory=list)
    title: str = ""

@dataclass
class WriteResult:
    content: str                  # 생성된 마크다운 본문
    metadata: PostMetadata
    images: list[ImageInfo]
    llm_usage: dict | None        # 토큰 사용량

class ContentPipeline:
    def __init__(
        self,
        llm_factory: LLMFactory,
        chunking_engine: ChunkingEngine,
        source_aggregator: SourceAggregator,
        template_manager: TemplateManager,
        reference_manager: ReferenceManager,
        markdown_generator: MarkdownGenerator,
        image_manager: ImageManager,
        config: Config,
    ): ...

    async def execute(self, request: WriteRequest) -> WriteResult:
        """
        글 작성 파이프라인 실행

        1. 소스 처리 (자동 생성인 경우)
           - 복수 소스 파싱/크롤링 → 병합
        2. 옵션 조립
           - 템플릿 렌더링 (선택된 경우)
           - 스타일 레퍼런스 로드 (선택된 경우)
        3. LLM 호출
           - 토큰 카운팅 → 직접 호출 or Map-Reduce
        4. 후처리
           - PostMetadata 생성 (면책 조항 플래그 포함)
           - 이미지 정리
        """

    async def get_feedback(self, request: WriteRequest) -> str:
        """페어 라이팅: 초안에 대한 LLM 피드백 반환"""
```

---

## 8. 에러 처리 전략

### 8.1 커스텀 예외 계층

```python
# core/exceptions.py

class WhiBlogError(Exception):
    """기본 예외"""

class ConfigError(WhiBlogError):
    """설정 관련 (API 키 미설정, YAML 파싱 실패 등)"""

class LLMError(WhiBlogError):
    """LLM API 호출 실패"""

class LLMRateLimitError(LLMError):
    """Rate limit 초과 — 재시도 가능"""

class LLMContextOverflowError(LLMError):
    """Map-Reduce 후에도 컨텍스트 초과"""

class SourceError(WhiBlogError):
    """소스 처리 실패 (PDF 파싱, URL 크롤링 등)"""

class PublishError(WhiBlogError):
    """게시 실패 (Git, Hugo 빌드 등)"""
```

### 8.2 재시도 전략

```python
# LLM API 호출 시 재시도
@retry(
    retry=retry_if_exception_type(LLMRateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(3),
)
async def _call_llm(self, request: LLMRequest) -> LLMResponse: ...
```

---

## 9. 테스트 전략

### 9.1 테스트 구조

```
tests/
├── unit/
│   ├── test_chunking.py           # 청킹 로직 단위 테스트
│   ├── test_markdown_generator.py # 마크다운 생성 테스트
│   ├── test_category_manager.py   # 카테고리 CRUD 테스트
│   ├── test_template_manager.py   # 템플릿 CRUD 테스트
│   └── test_keyword_filter.py     # 키워드 필터 테스트
├── integration/
│   ├── test_llm_clients.py        # 실제 API 호출 (CI에서는 mock)
│   ├── test_pdf_parser.py         # 샘플 PDF 파싱
│   ├── test_pipeline.py           # 전체 파이프라인 통합
│   └── test_git_manager.py        # Git 연동
├── fixtures/
│   ├── sample.pdf
│   ├── sample_template.yaml
│   └── sample_config.yaml
└── conftest.py                    # 공통 fixture, mock LLM client
```

### 9.2 Mock LLM 클라이언트

```python
# tests/conftest.py
class MockLLMClient:
    """테스트용 LLM 클라이언트 — 고정 응답 반환"""

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content="Mock generated content",
            model="mock-model",
            usage={"input_tokens": 100, "output_tokens": 50},
        )

    def count_tokens(self, text: str) -> int:
        return len(text) // 4
```

---

## 10. 보안 설계

### 10.1 민감 정보 보호 계층

```
[1단계] 환경변수 (os.environ)
    ↓ 미발견
[2단계] .env 파일 (python-dotenv)
    ↓ 미발견
[3단계] ConfigError 발생 + 사용자 안내
```

### 10.2 pre-commit 설정

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format
```

### 10.3 .gitignore 핵심 항목

```gitignore
# 민감 정보
.env
.secrets.baseline

# 런타임 데이터
data/

# Python
__pycache__/
*.pyc
.venv/

# Hugo 빌드
hugo-site/public/
hugo-site/resources/

# IDE
.vscode/
.idea/
```

---

## 11. 의존성 목록

### 11.1 requirements.txt

```
# LLM
anthropic>=0.40.0
openai>=1.50.0
tiktoken>=0.7.0

# UI
streamlit>=1.30.0

# 데이터
fredapi>=0.5.0
yfinance>=0.2.30
arxiv>=2.0.0

# PDF
PyMuPDF>=1.24.0

# 웹 크롤링
httpx>=0.27.0
beautifulsoup4>=4.12.0

# Git
GitPython>=3.1.40
PyGithub>=2.1.0

# 설정
pyyaml>=6.0
python-dotenv>=1.0.0

# 비동기
asyncio

# 재시도
tenacity>=8.2.0

# 테스트
pytest>=8.0.0
pytest-asyncio>=0.23.0

# 코드 품질
ruff>=0.3.0
mypy>=1.8.0
detect-secrets>=1.4.0
pre-commit>=3.6.0
```
