# TASKS: whi-blog — 마일스톤별 태스크 체크리스트

## 태스크 상태 규칙

- `[ ]` 미착수
- `[~]` 진행 중
- `[x]` 완료
- `[-]` 스킵/불필요

---

## M1: Hugo 사이트 기초

**목표**: Hugo 블로그가 GitHub Pages에 자동 배포되는 상태
**완료 기준**: 샘플 게시글(수식 포함)이 GitHub Pages에 배포됨

### M1.1 프로젝트 초기화

- [x] GitHub 레포지토리 생성 (`whi-blog`)
- [x] 기본 디렉토리 구조 생성 (`core/`, `ui/`, `config/`, `templates/`, `references/`, `data/`, `scripts/`, `tests/`)
- [x] `requirements.txt` 작성
- [x] `.gitignore` 작성 (.env, __pycache__, hugo-site/public/, data/ 등)
- [x] `.env.example` 작성 (ANTHROPIC_API_KEY, OPENAI_API_KEY, FRED_API_KEY, GITHUB_TOKEN)
- [x] `README.md` 초안 작성

### M1.2 Hugo 사이트 설정

- [x] Hugo 프로젝트 초기화 (`hugo-site/`)
- [x] Hugo Book 테마 git submodule 추가 (`themes/hugo-book`)
- [x] `hugo.toml` 작성 (Hugo v0.110+ 기본 파일명)
  - [x] 기본 설정 (baseURL, languageCode, title)
  - [x] Book 테마 파라미터 설정
  - [x] KaTeX 수식 렌더링 설정 (goldmark passthrough delimiters)
  - [x] markup unsafe 설정

### M1.3 계층형 카테고리 구조

- [x] Hugo content 디렉토리 계층 구조 설계
- [x] 카테고리별 `_index.md` 템플릿 정의 (weight, title, bookCollapseSection)
- [x] 샘플 카테고리 생성 (math > probability > random-matrix-theory, math > algebra, investment > macro-analysis, ai > ml-engineering)

### M1.4 Giscus 댓글 연동

- [ ] GitHub Discussions 활성화 *(GitHub 웹에서 수동 설정 필요)*
- [ ] Giscus 앱 설치 및 설정 *(giscus.app에서 repoId, categoryId 발급 필요)*
- [x] `hugo.toml`에 Giscus 파라미터 추가
- [x] Hugo Book 테마 댓글 레이아웃 오버라이드 (`layouts/_partials/docs/comments.html`)

### M1.5 면책 조항 기반 설정

- [x] `config/disclaimer.yaml` 작성 (llm_generated, llm_assisted 문구 및 스타일)
- [x] Hugo shortcode 작성 (`layouts/shortcodes/disclaimer.html`)
- [x] 면책 조항 CSS 스타일링 (warning, info, note + 다크모드)

### M1.6 샘플 게시글

- [x] 수식 포함 샘플 게시글 작성 (KaTeX 검증) — `wigner-semicircle.md`, `free-probability-intro.md`, `linear-algebra-basics.md`
- [-] 이미지 포함 샘플 게시글 작성 — M2.4 ImageManager 구현 후 추가
- [x] 면책 조항 포함 샘플 게시글 작성 — llm_generated(warning), llm_assisted(info) 2종
- [x] 다단계 카테고리 배치 확인 — 4개 게시글, 3단계 계층 검증 완료
- [x] 랜딩페이지 추가 — About + CV(주석) + Recent Posts 목록

### M1.7 CI/CD

- [x] `.github/workflows/deploy.yml` 작성
  - [x] checkout with submodules
  - [x] Hugo 설치 (extended)
  - [x] hugo --minify 빌드
  - [x] GitHub Pages 배포 (actions/deploy-pages@v4, 공식 방식으로 변경)
- [x] GitHub Pages 설정 *(Settings > Pages > Source: GitHub Actions 수동 설정 완료)*
- [x] 배포 검증 — 샘플 게시글이 정상 렌더링되는지 확인 완료

### M1.8 상단 네비게이션바 + 히어로 배너

- [x] `hugo.toml`에 `[[menu.main]]` 카테고리 메뉴 설정 (Math, AI/ML, Investment)
- [x] `layouts/baseof.html` — 테마 오버라이드, sticky 네비바 추가 (브랜드, 카테고리 링크, 다크모드 토글, 모바일 햄버거)
- [x] `layouts/index.html` — 히어로 배너 (제목, 소개, 토픽 뱃지) + 포스트 카드 그리드
- [x] `layouts/_default/list.html` — 섹션 페이지에서 하위 전체 글을 카드 형식으로 표시 (RegularPagesRecursive)
- [x] `layouts/_partials/docs/inject/body.html` — 다크모드 토글 버튼을 네비바로 이동, JS만 유지
- [x] `assets/_custom.scss` — 네비바/히어로/다크모드 스타일 추가, 반응형 대응

### M1.9 보안 설정

- [x] `.pre-commit-config.yaml` 작성 (detect-secrets v1.5.0, ruff v0.15.2)
- [x] `.secrets.baseline` 초기화 (PRD.md false positive 마킹 완료)
- [x] pre-commit 설치 및 테스트 — 전체 통과

---

## M2: Streamlit 기본 UI

**목표**: Streamlit으로 글 작성 → Hugo 마크다운 생성 → git push 가능
**완료 기준**: Streamlit에서 글 작성 → 블로그에 게시됨

### M2.1 Streamlit 앱 기본 구조

- [x] `ui/app.py` — 메인 앱, 사이드바 네비게이션
- [x] 멀티 페이지 구조 설정 (pages/ 디렉토리)
- [x] 공통 레이아웃/스타일 설정

### M2.2 코어 모듈 — 마크다운 생성기

- [x] `core/content/markdown_generator.py` 구현
  - [x] `PostMetadata` dataclass 정의
  - [x] `generate()` — front matter + content 마크다운 문자열 생성
  - [x] `save()` — Hugo content 디렉토리에 파일 저장
  - [x] front matter에 llm_disclaimer, llm_generated, llm_assisted 플래그 포함
- [x] 단위 테스트 (`tests/unit/test_markdown_generator.py`) — 16개 통과

### M2.3 코어 모듈 — 카테고리 매니저

- [x] `core/content/category_manager.py` 구현
  - [x] `list_all()` — 현재 카테고리 트리 반환
  - [x] `add()` — 카테고리 디렉토리 + _index.md 생성
  - [x] `remove()` — 카테고리 삭제 (하위 게시글 없는 경우만)
  - [x] `move()` — 카테고리 이동
- [x] 단위 테스트 (`tests/unit/test_category_manager.py`) — 18개 통과

### M2.4 코어 모듈 — 이미지 매니저

- [x] `core/content/image_manager.py` 구현
  - [x] `save_image()` — Hugo static에 이미지 저장, 마크다운 참조 경로 반환
  - [x] `generate_markdown_ref()` — 마크다운 이미지 참조 생성
  - [x] `list_images()` — 게시글별 이미지 목록 조회
  - [x] `delete_image()` — 이미지 삭제 (빈 디렉토리 자동 정리)
  - [x] `remove_markdown_image_ref()` — 본문에서 이미지 마크다운 참조 제거
- [x] 단위 테스트 (`tests/unit/test_image_manager.py`) — 33개 통과

### M2.5 글 작성 페이지 — 직접 작성 모드

- [x] `ui/pages/01_write.py` — 글 작성 모드 선택 UI (직접/페어/자동)
- [x] `ui/components/editor.py` — 마크다운 에디터 + 이미지 업로드 컴포넌트
- [x] `ui/components/preview.py` — KaTeX 수식 렌더링 미리보기 (다이얼로그 팝업)
- [x] 카테고리 선택 드롭다운 (CategoryManager 연동, 트리 플랫 변환)
- [x] 태그 입력
- [x] 이미지 업로드 → ImageManager 저장 → 마크다운 참조 자동 생성
- [x] 면책 조항 자동 설정 로직 (모드에 따라 llm_assisted/llm_generated 플래그 세팅)
- [x] sys.path 설정으로 core 패키지 import 해결

### M2.6 카테고리 관리 페이지

- [x] `ui/pages/02_categories.py`
  - [x] 카테고리 트리 표시 (들여쓰기 + 경로)
  - [x] 카테고리 추가 (이름, 부모 선택)
  - [x] 카테고리 삭제 (게시글 존재 시 안전 차단)
  - [x] 카테고리 이동 (출발지/목적지 선택)

### M2.7 설정 페이지 — 관심사 관리

- [x] `ui/pages/06_settings.py` — 탭 기반 설정 페이지
- [x] arxiv 관심사 관리 UI
  - [x] 관심 카테고리 추가/제거 (예: math.PR)
  - [x] 관심 키워드 추가/제거
  - [x] 관심사 자연어 설명 편집
  - [x] YAML 파일 저장/로드 (`config/arxiv_digest.yaml`)
- [x] 면책 조항 설정 UI
  - [x] 문구 편집
  - [x] 스타일 선택 (warning/info/note)
  - [x] YAML 파일 저장/로드 (`config/disclaimer.yaml` + Hugo data 동기화)
- [x] LLM 설정 탭 스텁 (M3에서 활성화)

### M2.8 Git 연동

- [x] `core/publishing/git_manager.py` 구현
  - [x] `commit_and_push()` — 파일 추가, 커밋, push
  - [x] `create_branch()` — 새 브랜치 생성
  - [x] `create_pr()` — gh CLI로 PR 생성
  - [x] `has_changes()` — 변경사항 확인
- [x] 단위 테스트 (`tests/unit/test_git_manager.py`) — 7개 통과
- [x] Streamlit에서 [게시하기] 버튼 → git commit + push 실행
- [x] 게시 결과 피드백 표시 (성공/실패)

### M2.9 Hugo 로컬 미리보기

- [x] `core/publishing/hugo_builder.py` 구현
  - [x] `build()` — hugo --minify 실행
  - [x] `serve()` — hugo server -D 실행 (프로세스 재사용)
  - [x] `stop()` — 서버 종료
  - [x] `get_preview_url()` — 게시글 미리보기 URL 반환
- [x] 단위 테스트 (`tests/unit/test_hugo_builder.py`) — 6개 통과
- [x] Streamlit에서 [미리보기 (Hugo)] 버튼 → draft 저장 후 Hugo 서버 URL 표시

### M2.10 글 관리 페이지

- [x] `core/content/post_manager.py` 구현
  - [x] `PostInfo` dataclass (file_path, title, date, categories, tags, draft)
  - [x] `PostManager.list_posts()` — .md 스캔, _index.md 제외, date 역순 정렬
  - [x] `PostManager.load_post()` — front matter 파싱 + 본문 분리 + disclaimer 제거
  - [x] `PostManager.save_post()` — MarkdownGenerator.generate()로 덮어쓰기
  - [x] `PostManager.delete_post()` — 파일 삭제
- [x] 단위 테스트 (`tests/unit/test_post_manager.py`) — 9개 통과
- [x] `ui/pages/07_manage.py` — 글 관리 페이지
  - [x] 카테고리 필터 + 초안만 보기 필터
  - [x] 글 선택 selectbox (제목, 날짜, draft 표시)
  - [x] 메타데이터 편집 (제목, 태그, 카테고리, 초안, 수식)
  - [x] 마크다운 에디터 (기존 본문 로드)
  - [x] 미리보기 다이얼로그
  - [x] 저장 → git commit + push
  - [x] 삭제 → 확인 다이얼로그 → git commit + push
  - [x] 이미지 관리 — 썸네일 조회, 개별 삭제(본문 참조 자동 제거 + git push), 업로드(git push)

---

## M3: LLM 연동

**목표**: 페어 라이팅, 자동 생성 워크플로우 동작
**완료 기준**: Streamlit에서 LLM 기반 글 작성 가능 (3가지 모드)

### M3.1 설정 관리

- [x] `core/config.py` 구현
  - [x] YAML 로더 (`_load_yaml()`)
  - [x] `get_api_key()` — 환경변수 → .env fallback → ConfigError
  - [x] `get_provider_config()` — 프로바이더별 설정 반환
  - [x] `get_chunking_config()` — 청킹 설정 반환
  - [x] (리뷰) config_dir 기본값을 절대경로로 수정
  - [x] (리뷰) load_dotenv()를 모듈 레벨로 이동 (인스턴스당 중복 호출 방지)
  - [x] (리뷰) YAML 파싱 에러 핸들링 추가 (yaml.YAMLError → ConfigError)
  - [x] (리뷰) 빈 문자열/공백만 있는 API 키 검증 추가
- [x] `config/llm_config.yaml` 작성 (claude/openai/llama 프로바이더, 모델, 청킹 설정)
  - [x] llama3.2 모델 추가
  - [x] chunking map/reduce 모델을 llama3.1로 변경 (API 비용 절감)
- [x] 단위 테스트 (`tests/unit/test_config.py`) — 12개 통과

### M3.2 LLM 클라이언트 — 인터페이스

- [x] `core/llm/base.py` 구현
  - [x] `LLMRequest` dataclass (system_prompt, user_prompt, model, temperature, max_tokens)
  - [x] `LLMResponse` dataclass (content, model, usage)
  - [x] `LLMClient` Protocol (generate, generate_stream, count_tokens, provider_name, max_context_tokens, available_models)
  - [x] (리뷰) `@runtime_checkable` 추가, 팩토리 테스트에 isinstance 검증 추가
- [x] `messages` 필드 추가 — 멀티턴 대화 지원 (기존 user_prompt 단일 메시지와 호환)
- [x] 단위 테스트 (`tests/unit/test_llm_base.py`) — 6개 통과

### M3.3 LLM 클라이언트 — Claude

- [x] `core/llm/claude_client.py` 구현
  - [x] `generate()` — anthropic AsyncAnthropic 비동기 호출
  - [x] `generate_stream()` — 스트리밍 응답 (messages.stream)
  - [x] `count_tokens()` — anthropic 토큰 카운팅
  - [x] `available_models` — config에서 모델 목록 로드
  - [x] 에러 핸들링 (AuthenticationError → LLMAuthError, RateLimitError → LLMRateLimitError)
  - [x] (리뷰) tenacity 재시도 데코레이터 적용 (exponential backoff, 최대 3회)
  - [x] (리뷰) 빈 응답 가드 추가 (response.content 체크)
  - [x] `messages` 지원 — 멀티턴 대화 시 messages 우선 사용
- [x] 단위 테스트 (`tests/unit/test_llm_clients.py`) — 9개 통과 (rate limit 재시도, API 에러, 빈 응답, 멀티턴 추가)
- [ ] 통합 테스트 (`tests/integration/test_llm_clients.py`) *(API 키 필요)*

### M3.4 LLM 클라이언트 — OpenAI

- [x] `core/llm/openai_client.py` 구현
  - [x] `generate()` — openai AsyncOpenAI 비동기 호출
  - [x] `generate_stream()` — 스트리밍 응답
  - [x] `count_tokens()` — tiktoken 사용
  - [x] `available_models` — config에서 모델 목록 로드
  - [x] (리뷰) tenacity 재시도 데코레이터 적용
  - [x] (리뷰) 빈 응답 가드 추가 (response.choices 체크)
  - [x] `messages` 지원 — 멀티턴 대화 시 messages 우선 사용
- [x] 단위 테스트 — 6개 통과 (rate limit 재시도, 빈 choices, 멀티턴 추가)
- [ ] 통합 테스트 *(API 키 필요)*

### M3.5 LLM 클라이언트 — Llama

- [x] `core/llm/llama_client.py` 구현
  - [x] `generate()` — ollama REST API (httpx AsyncClient)
  - [x] `generate_stream()` — Ollama 스트리밍 응답
  - [x] `count_tokens()` — 근사치 (len // 4)
  - [x] `available_models` — config에서 모델 목록 로드
  - [x] (리뷰) AsyncClient를 인스턴스 속성으로 재사용 (요청마다 재생성 방지)
  - [x] (리뷰) json import을 모듈 레벨로 이동
  - [x] (리뷰) 빈 응답 가드 추가 (.get() 체이닝)
  - [x] `messages` 지원 — 멀티턴 대화 시 messages 우선 사용
- [x] 단위 테스트 — 7개 통과 (빈 응답, HTTP 에러, 멀티턴 추가)
- [ ] 통합 테스트 *(Ollama 서버 필요)*

### M3.6 LLM 팩토리

- [x] `core/llm/factory.py` 구현
  - [x] `create()` — match-based provider dispatch (claude/openai/llama)
- [x] 단위 테스트 (`tests/unit/test_llm_factory.py`) — 4개 통과

### M3.7 에러 처리

- [x] `core/exceptions.py` 구현
  - [x] `WhiBlogError`, `ConfigError`, `LLMError`, `LLMRateLimitError`, `LLMAuthError`, `LLMContextOverflowError`, `SourceError`, `PublishError`
  - [x] (리뷰) `GitError(PublishError)`, `HugoError(PublishError)` 추가 — 중앙 예외 계층 통합
- [x] LLM 호출에 재시도 로직 적용 (tenacity) — ClaudeClient, OpenAIClient에 적용 완료

### M3.8 Streamlit — 페어 라이팅 모드

- [x] `ui/components/llm_selector.py` — 프로바이더/모델 선택 컴포넌트
  - [x] (리뷰) config/llm_config.yaml에서 모델 목록 로드, 실패 시 fallback
- [x] `ui/components/chat_panel.py` — 재사용 가능한 LLM 대화 패널 컴포넌트
  - [x] 대화 이력 표시 (role별 chat_message, 복사 팝오버, 토큰 표시)
  - [x] 메시지 입력 + 전송 버튼
- [x] 글 작성 페이지에 페어 라이팅 모드 UI 추가
  - [x] 좌우 2단 레이아웃 (에디터 + LLM 대화 패널)
  - [x] 멀티턴 대화 지원 (chat_panel 컴포넌트 연동)
  - [x] 현재 초안 포함 옵션 (대화에 에디터 내용 자동 첨부)
  - [x] 대화 초기화 버튼
  - [x] 미리보기 (다이얼로그 팝업)
  - [x] 면책 조항 플래그 자동 설정 (llm_assisted = true)
  - [x] (리뷰) [게시하기] 버튼 추가 (llm_assisted=True PostMetadata)
  - [x] (리뷰) 이미지 업로드 expander 추가
  - [x] (리뷰) [미리보기 (Hugo)] 버튼 추가
  - [x] (리뷰) `_slugify` → `slugify` public 함수로 변경
  - [x] (리뷰) GitError/HugoError import을 core.exceptions로 통일

### M3.9 Streamlit — 자동 생성 모드 (기본)

- [x] 글 작성 페이지에 자동 생성 모드 UI 추가
  - [x] 생성 전/후 2단계 UI (생성 전: 소스+프롬프트, 생성 후: 에디터+대화)
  - [x] 좌우 2단 레이아웃 (에디터 + LLM 대화 패널)
  - [x] 멀티턴 대화 지원 — 수정 요청 시 에디터 내용 자동 갱신
  - [x] 대화 초기화 버튼 (session_state 전체 리셋)
  - [x] 미리보기 + [게시하기] (llm_generated + llm_model 메타데이터 포함)
  - [x] 면책 조항 플래그 자동 설정 (llm_generated = true)
  - [x] (소스 입력은 M4에서 추가)
  - [x] (리뷰) [미리보기 (Hugo)] 버튼 추가
  - [x] (리뷰) 이미지 업로드 expander 추가
  - [x] (리뷰) 게시 완료 후 session_state 정리

---

## M4: 소스 연동

**목표**: PDF, URL, arxiv 소스에서 LLM 기반 글 생성 가능
**완료 기준**: 복수 소스(PDF 2개 + URL)를 입력하여 글 자동 생성 가능

### M4.1 PDF 파서

- [x] `core/sources/pdf_parser.py` 구현
  - [x] `parse()` — PyMuPDF로 텍스트 추출
  - [x] 페이지 범위 지정 (page_range 파라미터)
  - [x] 이미지 추출 (extract_images 파라미터)
  - [x] `PDFContent` dataclass (text, images, image_data, total_pages, extracted_range)
- [x] 단위 테스트 (14개, PyMuPDF로 테스트 PDF 동적 생성)

### M4.2 URL 크롤러

- [x] `core/sources/url_crawler.py` 구현
  - [x] `crawl()` — httpx + BeautifulSoup4 비동기 크롤링
  - [x] HTML 본문 텍스트 추출 (nav, footer, ads 제거)
  - [x] `CrawledContent` dataclass
- [x] 단위 테스트 (17개)

### M4.3 arxiv 클라이언트

- [x] `core/sources/arxiv_client.py` 구현
  - [x] `fetch_recent()` — 카테고리별 최신 논문 조회
  - [x] `fetch_by_id()` — 특정 논문 조회
  - [x] `download_pdf()` — PDF 다운로드
  - [x] `ArxivPaper` dataclass
- [x] 단위 테스트 (12개)

### M4.4 소스 어그리게이터

- [x] `core/sources/aggregator.py` 구현
  - [x] `SourceInput` dataclass (source_type, path_or_url, page_range, label)
  - [x] `AggregatedContent` dataclass (combined_text, sources, images, image_data, total_tokens_estimate)
  - [x] `aggregate()` — 복수 소스 파싱/크롤링 → 구분자 포함 병합 (부분 실패 허용)
- [x] 단위 테스트 (13개)

### M4.5 청킹 엔진

- [x] `core/llm/chunking.py` 구현
  - [x] `ChunkingConfig` dataclass
  - [x] `needs_chunking()` — 토큰 카운팅 기반 판단
  - [x] `split_chunks()` — 청크 분할 (헤딩 → 문단 → 줄바꿈 → 공백 경계 우선)
  - [x] `map_reduce()` — Map(병렬) + Reduce 파이프라인
- [x] Map 단계 경량 모델, Reduce 단계 고성능 모델 설정 적용
- [x] 단위 테스트 (`tests/unit/test_chunking.py`, 16개)

### M4.6 Streamlit — 소스 입력 UI

- [x] `ui/components/source_input.py` — 소스 입력 컴포넌트
  - [x] [+ PDF] [+ URL] [+ arxiv] 버튼
  - [x] 소스 목록 표시 (파일명/URL, 범위, 삭제 버튼)
  - [x] PDF 업로드 + 페이지 범위 지정
  - [x] URL 입력
  - [x] arxiv ID/URL 입력
- [x] 자동 생성 모드에 소스 입력 컴포넌트 연동

### M4.7 Streamlit — PDF 이미지 선택

- [x] `ui/components/image_picker.py` — 이미지 선택 컴포넌트
  - [x] PDF 추출 이미지 썸네일 표시
  - [x] 체크박스로 게시글에 포함할 이미지 선택
  - [x] 선택된 이미지 캡션 입력
- [x] 이미지 매니저 연동 (Hugo static 저장)

### M4.8 파이프라인 통합

- [x] `core/pipeline.py` 구현
  - [x] `WriteRequest` dataclass
  - [x] `WriteResult` dataclass
  - [x] `ContentPipeline.execute()` — 소스 처리 → 옵션 조립 → LLM 호출 → 후처리
  - [x] `ContentPipeline.get_feedback()` — 페어 라이팅 피드백
- [x] 토큰 카운팅 → 자동 분기 (직접 호출 / Map-Reduce) 연동
- [x] 통합 테스트 (`tests/integration/test_pipeline.py`, 15개)

---

## M5: 템플릿 시스템

**목표**: 프롬프트 템플릿과 스타일 레퍼런스를 관리하고 글 작성에 적용 가능
**완료 기준**: 템플릿 + 스타일 레퍼런스를 조합하여 원하는 문체/형식의 글 생성 가능

### M5.1 템플릿 매니저

- [x] `core/content/template_manager.py` 구현
  - [x] `PromptTemplate` dataclass (id, name, description, system_prompt, user_prompt_template, created_at, updated_at)
  - [x] `list_all()`, `get()`, `create()`, `update()`, `delete()`
  - [x] `render()` — 플레이스홀더 치환 ({content}, {style_reference} 등), format_map + defaultdict으로 미사용 플레이스홀더 빈 문자열 처리
- [x] `core/exceptions.py`에 `TemplateError`, `TemplateNotFoundError` 추가
- [x] `core/content/__init__.py`에 `TemplateManager`, `PromptTemplate` export 추가
- [x] 단위 테스트 (`tests/unit/test_template_manager.py`) — 27개 통과

### M5.2 기본 템플릿 세트

- [x] `templates/summary.yaml` — 요약 템플릿
- [x] `templates/column.yaml` — 칼럼/오피니언 템플릿
- [x] `templates/lecture_note.yaml` — 렉쳐노트 템플릿
- [x] `templates/paper_review.yaml` — 논문 리뷰 템플릿
- [x] `templates/data_report.yaml` — 데이터 분석 리포트 템플릿

### M5.3 스타일 레퍼런스 매니저

- [x] `core/content/reference_manager.py` 구현
  - [x] `StyleReference` dataclass (id, name, source_type, source_path, content_cache, file_type, created_at, updated_at)
  - [x] `list_all()`, `get()`, `add_file()`, `add_url()`, `remove()`, `get_content()`
  - [x] `references/index.yaml` 메타데이터 관리
  - [x] URL 레퍼런스 크롤링 (URLCrawler 재사용) + content_cache 저장
  - [x] PDF 레퍼런스 텍스트 추출 (PDFParser 재사용)
- [x] `core/exceptions.py`에 `ReferenceError`, `ReferenceNotFoundError` 추가
- [x] `core/content/__init__.py`에 `ReferenceManager`, `StyleReference` export 추가
- [x] 단위 테스트 (`tests/unit/test_reference_manager.py`) — 26개 통과

### M5.4 Streamlit — 템플릿 관리 페이지

- [x] `ui/pages/03_templates.py`
  - [x] 템플릿 목록 표시 (expander로 system_prompt, user_prompt_template 확인)
  - [x] 템플릿 생성 폼 (이름, 설명, system_prompt, user_prompt_template)
  - [x] 템플릿 편집 (selectbox 선택 → form으로 수정)
  - [x] 템플릿 삭제

### M5.5 Streamlit — 스타일 레퍼런스 관리 페이지

- [x] `ui/pages/04_references.py`
  - [x] 레퍼런스 목록 표시 (이름, 타입, 소스 — expander)
  - [x] 파일 레퍼런스 추가 (PDF, MD, TXT 업로드 → tempfile 경유 → add_file)
  - [x] URL 레퍼런스 추가 (크롤링 spinner 표시)
  - [x] 레퍼런스 삭제
  - [x] 레퍼런스 내용 미리보기 (expander 내 최대 2,000자)

### M5.6 글 작성 연동

- [x] 글 작성 페이지(페어 라이팅, 자동 생성)에 템플릿 선택 드롭다운 추가
- [x] 글 작성 페이지에 스타일 레퍼런스 선택 드롭다운 추가
- [x] ContentPipeline에 템플릿 렌더링 + 스타일 레퍼런스 주입 로직 연동
- [x] 통합 테스트 — 템플릿 + 레퍼런스 조합 글 생성

---

## M6: 외부 데이터 & 리포트

**목표**: 외부 데이터를 fetch하여 LLM 분석 리포트 생성
**완료 기준**: FRED 데이터 기반 경제 리포트 자동 생성 가능

### M6.1 DataFetcher 인터페이스

- [ ] `core/fetchers/base.py` 구현
  - [ ] `DataFetcher` Protocol (fetch, format_for_llm)

### M6.2 FRED Fetcher

- [ ] `core/fetchers/fred_fetcher.py` 구현
  - [ ] `fetch()` — fredapi로 시계열 데이터 조회
  - [ ] `format_for_llm()` — 텍스트 테이블 + 기술 통계 변환
- [ ] 통합 테스트

### M6.3 yfinance Fetcher

- [ ] `core/fetchers/yfinance_fetcher.py` 구현
  - [ ] `fetch()` — yfinance로 주가/지수 데이터 조회
  - [ ] `format_for_llm()` — 요약 텍스트 변환
- [ ] 통합 테스트

### M6.4 arxiv Fetcher

- [ ] `core/fetchers/arxiv_fetcher.py` 구현
  - [ ] `fetch()` — arxiv 검색 결과 조회
  - [ ] `format_for_llm()` — 제목 + abstract 텍스트 변환
- [ ] 통합 테스트

### M6.5 Streamlit — 리포트 생성 페이지

- [ ] `ui/pages/05_reports.py`
  - [ ] 데이터 소스 선택 (FRED, yfinance, arxiv)
  - [ ] 소스별 파라미터 입력 (series_id, ticker, query 등)
  - [ ] 프로바이더/모델 선택
  - [ ] 템플릿 선택 (optional)
  - [ ] [리포트 생성] → LLM 분석 결과 표시
  - [ ] [게시하기] → 마크다운 저장 + git push

---

## M7: 자동화

**목표**: 주기적 컨텐츠 자동 생성 및 PR 기반 게시
**완료 기준**: 매일 아침 관심 분야 arxiv 논문 요약 PR이 자동 생성됨

### M7.1 Git 매니저 — PR 기능

- [ ] `core/publishing/git_manager.py`에 PR 관련 메서드 추가
  - [ ] `create_branch()` — 새 브랜치 생성
  - [ ] `create_pr()` — PyGithub로 GitHub PR 생성
- [ ] 통합 테스트

### M7.2 arxiv 일일 다이제스트

- [ ] `core/scheduler/arxiv_digest.py` 구현
  - [ ] `DigestConfig` dataclass
  - [ ] `ArxivDigest.run()` — 전체 파이프라인
  - [ ] `_load_seen()` / `_save_seen()` — arxiv_seen.json 관리
  - [ ] `_keyword_filter()` — 키워드 기반 1차 필터
  - [ ] `_llm_filter()` — LLM 기반 2차 필터 (관심사 매칭 프롬프트)
  - [ ] 다이제스트 마크다운 생성 (날짜별 포스트)
  - [ ] 브랜치 생성 → 커밋 → PR 생성
- [ ] `data/arxiv_seen.json` 초기화
- [ ] 통합 테스트

### M7.3 자동 포스팅 엔진

- [ ] `core/scheduler/auto_post.py` 구현
  - [ ] `AutoPost.run()` — job config 기반 실행
  - [ ] fetcher 데이터 수집 → 템플릿 적용 → LLM 리포트 → 마크다운 → PR
- [ ] 통합 테스트

### M7.4 실행 스크립트

- [ ] `scripts/run_arxiv_digest.py` — CLI 엔트리포인트
- [ ] `scripts/run_auto_posts.py` — CLI 엔트리포인트

### M7.5 GitHub Actions — 자동 포스팅 워크플로우

- [ ] `.github/workflows/auto-post.yml` 작성
  - [ ] cron 스케줄 (매일 UTC 00:00)
  - [ ] workflow_dispatch (수동 트리거)
  - [ ] Python 설치 + 의존성 설치
  - [ ] Repository Secrets 설정 (ANTHROPIC_API_KEY, FRED_API_KEY, GITHUB_TOKEN)
  - [ ] run_arxiv_digest 실행
  - [ ] run_auto_posts 실행
- [ ] 워크플로우 수동 트리거로 검증
- [ ] 실제 cron 동작 검증 (하루 대기)

### M7.6 Streamlit — 자동 포스팅 설정

- [ ] 설정 페이지에 자동 포스팅 관련 UI 추가
  - [ ] arxiv 다이제스트 활성화/비활성화
  - [ ] 스케줄 설정
  - [ ] 최대 논문 수 설정
  - [ ] 최근 다이제스트 히스토리 표시

---

## M8: 최적화 & 수익화

**목표**: 블로그 최적화 및 AdSense 연계
**완료 기준**: AdSense 승인 및 광고 표시, Lighthouse 성능 점수 90+

### M8.1 SEO 최적화

- [ ] sitemap.xml 자동 생성 확인 (Hugo 기본 기능)
- [ ] robots.txt 작성
- [ ] 메타 태그 설정 (Open Graph, Twitter Card)
- [ ] 구조화 데이터 (JSON-LD) 추가
- [ ] canonical URL 설정

### M8.2 성능 최적화

- [ ] 이미지 최적화 (WebP 변환, lazy loading)
- [ ] Hugo 빌드 최적화 (minify, fingerprint)
- [ ] CSS/JS 최소화
- [ ] Lighthouse 성능 점수 측정 및 90+ 달성

### M8.3 Google AdSense

- [ ] AdSense 계정 설정
- [ ] ads.txt 추가
- [ ] 광고 코드 삽입 (Hugo 레이아웃 오버라이드)
- [ ] 광고 위치 최적화 (사이드바, 본문 사이)
- [ ] AdSense 심사 제출 및 승인

### M8.4 추가 개선

- [ ] Google Analytics 또는 대안 (Plausible, Umami) 연동
- [ ] RSS 피드 확인 및 최적화
- [ ] 소셜 공유 버튼 추가
- [ ] 검색 기능 (Hugo 내장 또는 Algolia)
- [ ] 커스텀 도메인 설정 (선택)

---

## 크로스 커팅: 문서화

마일스톤 진행과 병행하여 문서를 점진적으로 작성한다.

### MANUAL.md

- [ ] M1 완료 후: 설치, Hugo 사이트 구조, 배포 설정 섹션
- [ ] M2 완료 후: Streamlit UI 사용법, 직접 작성 모드 섹션
- [ ] M3 완료 후: LLM 설정, 페어 라이팅/자동 생성 사용법 섹션
- [ ] M4 완료 후: 소스 연동 (PDF, URL, arxiv) 사용법 섹션
- [ ] M5 완료 후: 템플릿/레퍼런스 관리 사용법 섹션
- [ ] M6 완료 후: 외부 데이터 리포트 사용법 섹션
- [ ] M7 완료 후: 자동 포스팅 설정, 트러블슈팅 섹션

### CLAUDE.md

- [ ] M1 착수 시: 프로젝트 컨텍스트, 코딩 컨벤션, 디렉토리 구조
- [ ] 마일스톤별 업데이트: 주요 결정사항, 모듈 간 관계, 주의사항 추가

### README.md

- [ ] M1 완료 후: 프로젝트 소개, 퀵스타트
- [ ] M8 완료 후: 전체 기능 소개, 스크린샷, 라이선스
