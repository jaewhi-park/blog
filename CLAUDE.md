# CLAUDE.md — whi-blog 프로젝트 컨텍스트

## 프로젝트 개요

whi-blog는 Hugo 정적 사이트 기반의 기술 블로그 엔진이다. Streamlit UI를 통한 글 작성 환경과 LLM 기반 컨텐츠 파이프라인을 제공한다. 수학, AI/ML, 투자 분석 등 기술 컨텐츠를 효율적으로 생산하는 것이 목표다.

## 문서 참조

- `PRD.md` — 기능 요구사항, 마일스톤 정의
- `TRD.md` — 기술 설계 상세 (인터페이스, 데이터 모델, 모듈 설계)
- `TASKS.md` — 마일스톤별 체크리스트 (현재 진행 상황)
- `MANUAL.md` — 사용자 매뉴얼 (점진적 작성)

작업 전 반드시 해당 문서를 참조하여 컨텍스트를 파악할 것.

---

## 디렉토리 구조

```
whi-blog/
├── core/                          # 핵심 Python 라이브러리 (UI 의존성 없음)
│   ├── __init__.py
│   ├── config.py                  # 전역 설정 관리
│   ├── exceptions.py              # 커스텀 예외 계층
│   ├── llm/                       # LLM 클라이언트
│   │   ├── base.py                # LLMClient Protocol, LLMRequest, LLMResponse
│   │   ├── factory.py             # LLMFactory
│   │   ├── claude_client.py
│   │   ├── openai_client.py
│   │   ├── llama_client.py
│   │   └── chunking.py            # ChunkingEngine (Map-Reduce)
│   ├── content/                   # 컨텐츠 관리
│   │   ├── markdown_generator.py  # PostMetadata, MarkdownGenerator
│   │   ├── category_manager.py    # CategoryManager
│   │   ├── image_manager.py       # ImageManager
│   │   ├── template_manager.py    # TemplateManager
│   │   └── reference_manager.py   # ReferenceManager (스타일 레퍼런스)
│   ├── sources/                   # 외부 소스 파싱
│   │   ├── pdf_parser.py          # PDFParser (PyMuPDF)
│   │   ├── url_crawler.py         # URLCrawler (httpx + BS4)
│   │   ├── arxiv_client.py        # ArxivClient
│   │   └── aggregator.py          # SourceAggregator (복수 소스 병합)
│   ├── fetchers/                  # 외부 데이터 수집
│   │   ├── base.py                # DataFetcher Protocol
│   │   ├── fred_fetcher.py
│   │   ├── yfinance_fetcher.py
│   │   └── arxiv_fetcher.py
│   ├── publishing/                # 게시 파이프라인
│   │   ├── git_manager.py         # GitManager (커밋, push, PR)
│   │   └── hugo_builder.py        # HugoBuilder (빌드, 로컬 서버)
│   ├── scheduler/                 # 자동화
│   │   ├── arxiv_digest.py        # ArxivDigest (일일 다이제스트)
│   │   └── auto_post.py           # AutoPost (주기적 자동 포스팅)
│   └── pipeline.py                # ContentPipeline (글 작성 오케스트레이터)
├── ui/                            # Streamlit 앱 (core를 호출만 함)
│   ├── app.py
│   ├── pages/
│   │   ├── 01_write.py
│   │   ├── 02_categories.py
│   │   ├── 03_templates.py
│   │   ├── 04_references.py
│   │   ├── 05_reports.py
│   │   └── 06_settings.py
│   └── components/
│       ├── editor.py
│       ├── preview.py
│       ├── source_input.py
│       ├── llm_selector.py
│       └── image_picker.py
├── templates/                     # 프롬프트 템플릿 YAML
├── references/                    # 스타일 레퍼런스 파일 + index.yaml
├── config/                        # 설정 파일
│   ├── llm_config.yaml
│   ├── arxiv_digest.yaml
│   ├── disclaimer.yaml
│   └── site_config.yaml
├── data/                          # 런타임 데이터 (git 추적 대상)
│   └── arxiv_seen.json
├── hugo-site/                     # Hugo 프로젝트
│   ├── config.toml
│   ├── content/
│   ├── static/images/
│   ├── layouts/shortcodes/
│   └── themes/hugo-book/          # git submodule
├── .github/workflows/
│   ├── deploy.yml
│   └── auto-post.yml
├── scripts/
│   ├── run_arxiv_digest.py
│   └── run_auto_posts.py
└── tests/
    ├── unit/
    ├── integration/
    ├── fixtures/
    └── conftest.py
```

---

## 핵심 아키텍처 원칙

### 1. Core/UI 분리

`core/`는 Streamlit에 의존하지 않는 순수 Python 패키지다. 모든 비즈니스 로직은 `core/`에 있고, `ui/`는 `core/`를 호출만 한다. 이렇게 하면 GitHub Actions 스크립트에서도 `core/`를 그대로 사용할 수 있다.

```
# 올바른 의존 방향
ui/ → core/
scripts/ → core/
.github/workflows/ → scripts/ → core/

# 금지 — core가 ui에 의존하면 안 됨
core/ → ui/  (NEVER)
```

### 2. Protocol 기반 추상화

LLMClient, DataFetcher 등 외부 의존성이 있는 모듈은 반드시 `typing.Protocol`로 인터페이스를 정의한다. 구현체는 팩토리 패턴으로 생성한다.

```python
# 올바른 패턴
class LLMClient(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse: ...

# 금지 — 구체 클래스에 직접 의존
from core.llm.claude_client import ClaudeClient  # pipeline.py에서 이렇게 하지 말 것
```

### 3. 설정 외부화

하드코딩 금지. 모든 설정은 YAML 파일 또는 환경변수로 관리한다.

```python
# 올바른 패턴
model = config.llm["providers"]["claude"]["default_model"]

# 금지
model = "claude-sonnet-4-20250514"  # 하드코딩
```

### 4. 비동기 우선

LLM API 호출, 웹 크롤링, Map-Reduce 등 I/O 바운드 작업은 모두 `async/await`로 구현한다. Streamlit에서 호출할 때는 `asyncio.run()`으로 감싼다.

---

## 코딩 컨벤션

### Python 스타일

- Python 3.11+
- 타입 힌트 필수 (모든 함수 시그니처, 클래스 필드)
- `dataclass`를 적극 사용 (DTO, 설정 객체 등)
- f-string 사용 (`.format()` 금지)
- 독스트링: 모든 public 클래스/메서드에 작성
- 가상환경 사용 (venv)

### 네이밍

```
파일명:        snake_case.py
클래스:        PascalCase
함수/메서드:   snake_case
상수:          UPPER_SNAKE_CASE
private:       _leading_underscore
```

### import 순서

```python
# 1. 표준 라이브러리
import asyncio
from pathlib import Path

# 2. 서드파티
import anthropic
import streamlit as st

# 3. 프로젝트 내부
from core.llm.base import LLMClient, LLMRequest
from core.config import Config
```

### 에러 처리

- `core/exceptions.py`에 정의된 커스텀 예외를 사용
- LLM API 호출은 반드시 try/except로 감싸고 적절한 예외로 변환
- Rate limit은 tenacity로 자동 재시도 (최대 3회, exponential backoff)

```python
# 올바른 패턴
from core.exceptions import LLMError, LLMRateLimitError

try:
    response = await self._client.messages.create(...)
except anthropic.RateLimitError as e:
    raise LLMRateLimitError(str(e)) from e
except anthropic.APIError as e:
    raise LLMError(str(e)) from e
```

### 테스트

- 파일 위치: `tests/unit/` (단위), `tests/integration/` (통합)
- 네이밍: `test_{module_name}.py`
- fixture: `tests/fixtures/`에 샘플 파일, `tests/conftest.py`에 공통 fixture
- LLM 호출이 포함된 테스트는 `MockLLMClient`를 사용하거나, `@pytest.mark.integration`으로 분리
- `pytest-asyncio`로 비동기 테스트

---

## 모듈 간 관계 및 데이터 흐름

### 글 작성 파이프라인

```
ui/pages/01_write.py
  → core/pipeline.py (ContentPipeline)
    → core/sources/aggregator.py (복수 소스 파싱/병합)
      → core/sources/pdf_parser.py
      → core/sources/url_crawler.py
      → core/sources/arxiv_client.py
    → core/content/template_manager.py (템플릿 로드/렌더링)
    → core/content/reference_manager.py (스타일 레퍼런스 로드)
    → core/llm/chunking.py (토큰 체크 → 직접 호출 or Map-Reduce)
      → core/llm/factory.py → core/llm/{provider}_client.py
    → core/content/markdown_generator.py (Hugo 마크다운 생성)
    → core/content/image_manager.py (이미지 Hugo static 배치)
  → core/publishing/git_manager.py (커밋, push)
```

### 자동 포스팅 (GitHub Actions)

```
scripts/run_arxiv_digest.py
  → core/scheduler/arxiv_digest.py
    → core/sources/arxiv_client.py (논문 fetch)
    → core/llm/factory.py → LLMClient (필터링 + 요약)
    → core/content/markdown_generator.py (마크다운 생성)
    → core/publishing/git_manager.py (브랜치 + PR 생성)
```

---

## 주요 설계 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| 테마 관리 | git submodule | Hugo 생태계 표준, 업스트림 업데이트 용이 |
| 외부 데이터 수집 | function (fetcher 클래스) | MCP 서버는 이 프로젝트에 불필요한 오버헤드 |
| 긴 문서 처리 | Map-Reduce 자동 분기 | 토큰 카운팅 기반, 프로바이더별 한도 자동 대응 |
| Map/Reduce 모델 | 분리 (경량/고성능) | API 비용 최적화 |
| 논문 중복 관리 | JSON 파일 | DB 불필요 (연간 수만 건), git으로 상태 관리 |
| 자동 포스팅 | GitHub Actions cron + PR | 별도 인프라 없음, PR로 안전장치 |
| 템플릿 vs Claude Skills | 자체 템플릿 시스템 | API 직접 호출 구조, 프로바이더 무관 적용 |
| 면책 조항 | front matter 플래그 + Hugo shortcode | 글 작성 모드별 자동 삽입, 한 곳에서 문구 관리 |
| 스타일 레퍼런스 | 별도 관리 (템플릿과 분리) | 템플릿=지시, 레퍼런스=예시 — 독립적 관심사 |
| 댓글 | Giscus | GitHub Discussions 기반, 별도 인프라 불필요 |

---

## 보안 주의사항

### 절대 금지

- API 키를 코드에 하드코딩
- `.env` 파일을 git에 커밋
- Streamlit UI에 API 키를 표시
- 로그에 API 키를 출력

### API 키 로딩 순서

```
1. os.environ (export된 환경변수)
2. .env 파일 (python-dotenv)
3. 미발견 → ConfigError 발생
```

### GitHub Actions에서는

- Repository Secrets 사용 (`${{ secrets.ANTHROPIC_API_KEY }}`)
- 절대 워크플로우 로그에 키가 노출되지 않도록 주의

### pre-commit

- `detect-secrets`가 설정되어 있음
- 커밋 전 자동으로 민감 정보 스캔
- 바이패스 금지

---

## 자주 사용하는 명령어

### 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# pre-commit 설치
pre-commit install

# Streamlit 앱 실행
streamlit run ui/app.py

# Hugo 로컬 서버
cd hugo-site && hugo server -D

# 테스트 실행
pytest tests/unit/
pytest tests/integration/ -m "not integration"  # mock 테스트만
pytest tests/integration/ -m integration         # 실제 API 테스트
```

### 배포 관련

```bash
# Hugo 빌드
cd hugo-site && hugo --minify

# arxiv 다이제스트 수동 실행
python -m scripts.run_arxiv_digest

# 자동 포스팅 수동 실행
python -m scripts.run_auto_posts
```

---

## 마일스톤 진행 순서

```
M1 (Hugo 기초) → M2 (Streamlit UI) → M3 (LLM 연동) → M4 (소스 연동)
→ M5 (템플릿) → M6 (외부 데이터) → M7 (자동화) → M8 (최적화)
```

각 마일스톤은 이전 마일스톤이 완료된 상태에서 시작한다. 상세 태스크는 `TASKS.md` 참조.

---

## 작업 시 주의사항

### 새 모듈 추가 시

1. TRD.md의 해당 인터페이스를 먼저 확인
2. Protocol이 정의되어 있으면 반드시 Protocol을 구현
3. `__init__.py`에 public API를 export
4. 단위 테스트 작성 (최소 핵심 메서드)
5. 필요 시 TASKS.md의 체크리스트 업데이트

### Streamlit 페이지 추가 시

1. `ui/pages/` 에 번호 프리픽스로 파일 생성 (예: `07_new_page.py`)
2. 비즈니스 로직은 반드시 `core/`에 구현하고, 페이지에서는 호출만
3. 재사용 가능한 UI 요소는 `ui/components/`에 분리

### 설정 변경 시

1. YAML 스키마를 먼저 정의/수정
2. `core/config.py`에서 로딩 로직 업데이트
3. `.env.example` 업데이트 (새 환경변수 추가 시)
4. MANUAL.md 해당 섹션 업데이트

### Hugo 관련 변경 시

1. `hugo-site/` 내에서만 작업
2. 테마 커스터마이징은 `layouts/` 오버라이드로 (테마 파일 직접 수정 금지)
3. 정적 파일은 `static/` 에 배치
4. 변경 후 `hugo server -D`로 로컬 검증

---

## Claude Code 에이전트 팀 구성 가이드

복잡한 태스크는 서브 에이전트로 분할하여 병렬 작업할 수 있다.

### 권장 에이전트 분할

**에이전트 1: Core 모듈**
- `core/` 내 Python 모듈 구현
- 인터페이스 정의, 비즈니스 로직
- 단위 테스트

**에이전트 2: Streamlit UI**
- `ui/` 내 페이지 및 컴포넌트
- core 모듈 호출 연동
- UI/UX 검증

**에이전트 3: Hugo & 인프라**
- `hugo-site/` 설정 및 레이아웃
- GitHub Actions 워크플로우
- 배포 파이프라인

### 에이전트 간 의존성

```
에이전트 3 (Hugo)  ← 독립적, M1에서 먼저 시작 가능
에이전트 1 (Core)  ← M2부터 시작, 인터페이스 먼저 정의
에이전트 2 (UI)    ← 에이전트 1의 인터페이스 정의 후 병렬 진행 가능
```

### 병렬 작업 가능 구간

- M1: 에이전트 3 단독
- M2: 에이전트 1 (markdown_generator, category_manager) + 에이전트 2 (Streamlit 기본 구조) 병렬
- M3: 에이전트 1 (LLM 클라이언트) + 에이전트 2 (LLM UI) 병렬 (인터페이스 합의 후)
- M4: 에이전트 1 (소스 파서, 청킹) + 에이전트 2 (소스 입력 UI) 병렬
