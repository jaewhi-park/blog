# PRD: whi-blog — Hugo Blog Engine with LLM-Powered Content Pipeline

## 1. 개요

### 1.1 프로젝트 명

**whi-blog**

### 1.3 프로젝트 목적

수학, AI/ML, 투자 분석 등 기술 블로그를 운영하기 위한 통합 블로그 엔진을 구축한다. Hugo 정적 사이트를 기반으로 하되, Streamlit UI를 통한 편리한 글 작성 환경과 LLM 기반 컨텐츠 파이프라인을 제공하여 고품질 기술 컨텐츠를 효율적으로 생산한다.

### 1.4 핵심 가치

- **효율적 컨텐츠 생산**: LLM을 활용한 페어 라이팅, 자동 생성, 소스 기반 글 작성
- **자동화**: arxiv 논문 다이제스트, 외부 데이터 리포트 등 주기적 컨텐츠 자동 생성
- **유연성**: 멀티 LLM 프로바이더, 자유로운 카테고리 구조, 커스텀 템플릿
- **안전성**: PR 기반 게시 워크플로우, 민감 정보 보호

### 1.5 기술 스택

| 영역 | 기술 |
|------|------|
| 정적 사이트 | Hugo + Hugo Book Theme |
| 호스팅 | GitHub Pages |
| CI/CD | GitHub Actions |
| CMS UI | Streamlit |
| LLM | Claude API, GPT API, Llama (로컬) |
| 언어 | Python |
| 개발 도구 | Claude Code |

---

## 2. 기능 요구사항

### FR-1. 인프라 & 배포

| ID | 요구사항 | 설명 |
|----|---------|------|
| FR-1.1 | Hugo 정적 사이트 | Hugo 기반 블로그 사이트 구축 |
| FR-1.2 | Hugo Book 테마 | git submodule로 테마 관리 |
| FR-1.3 | GitHub Pages 배포 | GitHub Actions를 통한 자동 빌드/배포 |
| FR-1.4 | 민감 정보 관리 | 환경변수 → .env fallback, Repository Secrets, pre-commit hook (detect-secrets) |

### FR-2. 컨텐츠 관리

| ID | 요구사항 | 설명 |
|----|---------|------|
| FR-2.1 | 계층형 카테고리 | 자유롭게 추가/제거 가능한 다단계 카테고리 (예: math > probability > random matrix theory) |
| FR-2.2 | 수식 지원 | KaTeX를 통한 수학 수식 렌더링 |
| FR-2.3 | 이미지 지원 | 사용자 업로드 이미지 + PDF 추출 이미지, Hugo static 폴더 자동 배치 |
| FR-2.4 | 댓글 기능 | Giscus (GitHub Discussions 기반) 연동 |
| FR-2.5 | 로컬 미리보기 | Hugo 로컬 서버를 통한 게시 전 미리보기 |

### FR-3. 글 작성 (Streamlit UI)

| ID | 요구사항 | 설명 |
|----|---------|------|
| FR-3.1 | 직접 작성 | 마크다운 에디터로 작성 → 즉시 게시 |
| FR-3.2 | 페어 라이팅 | 초안 작성 + 템플릿 선택(optional) → LLM 가공/피드백 → 수정 후 게시 |
| FR-3.3 | 자동 생성 | 소스(PDF, arxiv URL, web URL) 입력 + 템플릿 선택(optional) → LLM 초안 → 리뷰/수정 후 게시 |
| FR-3.4 | PDF 범위 지정 | PDF 소스의 참고 페이지/섹션 범위 지정 |
| FR-3.5 | 이미지 관리 | PDF 이미지 자동 추출 → UI에서 선택, 사용자 이미지 업로드 → 마크다운 삽입 |
| FR-3.6 | 카테고리 관리 | Streamlit UI에서 카테고리 추가/제거/재구조화 |
| FR-3.7 | LLM 면책 조항 | LLM 생성/가공 게시글에 면책 문구 자동 삽입 (front matter 플래그 기반, Hugo 레이아웃에서 렌더링). 문구는 설정에서 수정 가능 |
| FR-3.8 | 작성 중 미리보기 | Streamlit 내 실시간 미리보기 (수식 렌더링, 이미지 배치 확인). Hugo 로컬 서버 연동으로 최종 렌더링 확인 가능 |
| FR-3.9 | 복수 소스 입력 | 글 작성 시 여러 소스(PDF, URL, arxiv)를 동시에 추가. 소스별 참고 범위 개별 지정 가능 |

### FR-4. 템플릿 시스템

| ID | 요구사항 | 설명 |
|----|---------|------|
| FR-4.1 | 템플릿 CRUD | summary, 칼럼, 렉쳐노트 등 프롬프트 템플릿 생성/조회/수정/삭제 |
| FR-4.2 | 템플릿 구조 | 각 템플릿은 system_prompt + user_prompt_template로 구성 |
| FR-4.3 | 템플릿 적용 | 글 작성 시(FR-3.2, FR-3.3) 템플릿 선택 적용, 미선택 시 기본 프롬프트 사용 |
| FR-4.4 | 스타일 레퍼런스 관리 | 참고할 글 형식 등록/선택. 지원 형식: PDF, MD, TXT, URL(웹 페이지/기사). 글 작성 시 템플릿과 별도로 선택 가능. LLM에 문체/구조 예시로 전달 |

### FR-5. LLM 연동

| ID | 요구사항 | 설명 |
|----|---------|------|
| FR-5.1 | 멀티 프로바이더 | Claude API, GPT API, Llama(로컬) 지원 |
| FR-5.2 | 통합 인터페이스 | LLMClient Protocol로 프로바이더 추상화 |
| FR-5.3 | 모델 선택 | 프로바이더 선택 + 해당 프로바이더 내 모델 선택 (예: Claude → Sonnet/Haiku, OpenAI → GPT-4o/4o-mini) |
| FR-5.4 | 긴 문서 자동 처리 | 토큰 카운팅 기반 자동 분기 — 컨텍스트 이내면 직접 처리, 초과 시 Map-Reduce |
| FR-5.5 | Map-Reduce 청킹 | 긴 문서를 청크 분할 → 개별 요약(Map) → 종합 생성(Reduce) |
| FR-5.6 | 단계별 모델 분리 | Map 단계는 경량 모델(Haiku, GPT-4o-mini), Reduce 단계는 고성능 모델(Sonnet, GPT-4o) 설정 가능 |
| FR-5.7 | 병렬 처리 | Map 단계 청크 요청을 asyncio.gather로 병렬 호출 |

### FR-6. 외부 데이터 & 자동화

| ID | 요구사항 | 설명 |
|----|---------|------|
| FR-6.1 | 데이터 Fetcher | FRED, yfinance, arxiv 등 외부 데이터 수집 모듈 (function 기반, 공통 인터페이스) |
| FR-6.2 | LLM 리포트 생성 | 외부 데이터 fetch → LLM 분석 → 리포트 마크다운 생성 |
| FR-6.3 | arxiv 일일 다이제스트 | 2단계 필터링(키워드 사전 필터 → LLM 정밀 필터) → 관심 논문 요약 → PR 생성 |
| FR-6.4 | 관심사 관리 | 관심 카테고리, 키워드, 자연어 설명 CRUD (YAML 기반 저장) |
| FR-6.5 | 자동 포스팅 | GitHub Actions cron으로 주기적 실행 → 컨텐츠 생성 → PR → 사용자 confirm 후 게시 |
| FR-6.6 | 중복 방지 | 처리 완료 논문 ID를 JSON 파일로 관리하여 중복 처리 방지 |

### FR-7. 설정 & 보안

| ID | 요구사항 | 설명 |
|----|---------|------|
| FR-7.1 | API 키 관리 | 환경변수 우선 → .env fallback → 미감지 시 에러 |
| FR-7.2 | GitHub Secrets | GitHub Actions에서는 Repository Secrets 사용 |
| FR-7.3 | pre-commit hook | detect-secrets 등으로 민감 정보 커밋 방지 |
| FR-7.4 | .gitignore | .env, API 키 파일 등 반드시 제외 |

---

## 3. 시스템 아키텍처

### 3.1 디렉토리 구조

```
blog-engine/
├── core/                          # 핵심 Python 라이브러리
│   ├── llm/                       # LLM 클라이언트, 프로바이더 구현
│   │   ├── base.py                # LLMClient Protocol
│   │   ├── claude_client.py
│   │   ├── openai_client.py
│   │   ├── llama_client.py
│   │   └── chunking.py            # Map-Reduce, 토큰 카운팅
│   ├── content/                   # 컨텐츠 생성/관리
│   │   ├── markdown_generator.py  # Hugo 마크다운 생성
│   │   ├── category_manager.py    # 계층형 카테고리 관리
│   │   ├── image_manager.py       # 이미지 처리, Hugo static 배치
│   │   ├── template_manager.py    # 프롬프트 템플릿 CRUD
│   │   └── reference_manager.py   # 스타일 레퍼런스 관리
│   ├── sources/                   # 외부 소스 처리
│   │   ├── pdf_parser.py          # PDF 텍스트/이미지 추출
│   │   ├── url_crawler.py         # 웹 URL 크롤링
│   │   └── arxiv_client.py        # arxiv API 클라이언트
│   ├── fetchers/                  # 외부 데이터 수집
│   │   ├── base.py                # DataFetcher Protocol
│   │   ├── fred_fetcher.py
│   │   ├── yfinance_fetcher.py
│   │   └── arxiv_fetcher.py
│   ├── publishing/                # 게시 파이프라인
│   │   ├── git_manager.py         # Git 커밋, PR 생성
│   │   └── hugo_builder.py        # Hugo 빌드, 로컬 서버
│   └── scheduler/                 # 자동화 스케줄
│       ├── arxiv_digest.py        # arxiv 일일 다이제스트
│       └── auto_post.py           # 주기적 자동 포스팅
├── ui/                            # Streamlit 앱
│   ├── app.py                     # 메인 엔트리포인트
│   ├── pages/
│   │   ├── write.py               # 글 작성 (직접/페어/자동)
│   │   ├── categories.py          # 카테고리 관리
│   │   ├── templates.py           # 템플릿 관리
│   │   ├── settings.py            # 관심사, LLM 설정
│   │   └── reports.py             # 외부 데이터 리포트
│   └── components/                # 재사용 UI 컴포넌트
├── templates/                     # 프롬프트 템플릿 YAML 파일
├── references/                    # 스타일 레퍼런스 파일 (PDF, MD, TXT)
├── config/                        # 설정 파일
│   ├── llm_config.yaml            # LLM 프로바이더, 모델, 청킹 설정
│   └── arxiv_digest.yaml          # 관심사, 스케줄 설정
├── data/                          # 런타임 데이터
│   └── arxiv_seen.json            # 처리 완료 논문 ID
├── hugo-site/                     # Hugo 프로젝트
│   ├── config.toml
│   ├── content/                   # 게시글 마크다운
│   ├── static/                    # 이미지 등 정적 파일
│   └── themes/
│       └── hugo-book/             # git submodule
├── .github/
│   └── workflows/
│       ├── deploy.yml             # Hugo 빌드 + GitHub Pages 배포
│       └── auto-post.yml          # 자동 포스팅 cron
├── scripts/                       # CLI 스크립트
├── tests/                         # 테스트
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── requirements.txt
├── CLAUDE.md                      # Claude Code 프로젝트 컨텍스트
├── TASKS.md                       # 마일스톤별 태스크
├── MANUAL.md                      # 사용자 매뉴얼
└── README.md
```

### 3.2 핵심 데이터 흐름

#### 글 작성 흐름 (페어 라이팅 / 자동 생성)

```
[사용자 입력]
  ├── 직접 작성: 마크다운 텍스트
  ├── 페어 라이팅: 초안 텍스트
  └── 자동 생성: 소스 (PDF/URL/arxiv) × 복수 가능

        ↓

[소스 처리] (자동 생성인 경우, 복수 소스 병합)
  ├── PDF → pdf_parser (범위 지정, 이미지 추출)
  ├── URL → url_crawler
  └── arxiv → arxiv_client

        ↓

[옵션 적용]
  ├── 템플릿 선택 (optional) → system_prompt + user_prompt_template
  └── 스타일 레퍼런스 선택 (optional) → 문체/구조 예시로 주입

        ↓

[토큰 카운팅 → 자동 분기]
  ├── 컨텍스트 이내 → 직접 LLM 호출
  └── 초과 → Map-Reduce 청킹
       ├── Map: 청크별 요약 (경량 모델, 병렬)
       └── Reduce: 종합 생성 (고성능 모델)

        ↓

[LLM 호출] (선택된 프로바이더 + 모델)
  ├── Claude API (Sonnet / Haiku)
  ├── GPT API (4o / 4o-mini)
  └── Llama (로컬)

        ↓

[초안 생성] → Streamlit UI에서 리뷰/수정

        ↓

[게시]
  ├── Hugo 마크다운 생성 (front matter + content)
  ├── 면책 조항 플래그 자동 설정 (LLM 사용 시)
  ├── 이미지 → hugo-site/static/ 배치
  └── git commit + push (또는 PR)
```

#### 자동 포스팅 흐름 (arxiv 다이제스트)

```
[GitHub Actions cron (매일)]
        ↓
[arxiv API] → math.PR, math.SP 등 최신 논문 fetch
        ↓
[중복 필터] → arxiv_seen.json으로 이미 처리한 논문 제외
        ↓
[1단계 필터] → 키워드 매칭 (비용 0)
        ↓
[2단계 필터] → LLM에 abstract 전달, 관심사 description 기반 정밀 필터링
        ↓
[요약 생성] → LLM이 선별된 논문 요약 마크다운 생성
        ↓
[PR 생성] → GitHub PR 자동 생성
        ↓
[사용자 confirm] → PR 머지 → GitHub Actions → Hugo 빌드 → 배포
```

---

## 4. 설정 파일 구조

### 4.1 LLM 설정 (config/llm_config.yaml)

```yaml
providers:
  claude:
    api_key_env: "ANTHROPIC_API_KEY"
    default_model: "claude-sonnet-4-20250514"
    max_context_tokens: 200000
    available_models:
      - id: "claude-sonnet-4-20250514"
        name: "Claude Sonnet"
        tier: "standard"
      - id: "claude-haiku-4-5-20251001"
        name: "Claude Haiku"
        tier: "light"
  openai:
    api_key_env: "OPENAI_API_KEY"
    default_model: "gpt-4o"
    max_context_tokens: 128000
    available_models:
      - id: "gpt-4o"
        name: "GPT-4o"
        tier: "standard"
      - id: "gpt-4o-mini"
        name: "GPT-4o Mini"
        tier: "light"
  llama:
    endpoint: "http://localhost:11434"
    default_model: "llama3.1"
    max_context_tokens: 128000
    available_models:
      - id: "llama3.1"
        name: "Llama 3.1"
        tier: "standard"

default_provider: "claude"

chunking:
  map_model: "claude-haiku"       # Map 단계 경량 모델
  reduce_model: "claude-sonnet"   # Reduce 단계 고성능 모델
  chunk_size_tokens: 4000
  context_threshold: 0.7          # 컨텍스트의 70% 초과 시 청킹
```

### 4.2 arxiv 다이제스트 설정 (config/arxiv_digest.yaml)

```yaml
categories:
  - math.PR    # Probability
  - math.SP    # Spectral Theory
  - math-ph    # Mathematical Physics

interests:
  keywords:
    - "random matrix"
    - "free probability"
    - "eigenvalue distribution"
    - "Wigner"
    - "spectral"
    - "Tracy-Widom"
  description: >
    I'm interested in random matrix theory, especially
    universality results, free probability connections,
    and spectral analysis of large random matrices.

schedule: "0 9 * * *"  # 매일 오전 9시 (UTC)
max_papers_per_digest: 5
```

### 4.3 면책 조항 설정 (config/disclaimer.yaml)

```yaml
disclaimers:
  llm_generated:
    enabled: true
    text: "이 게시글은 LLM에 의해 생성되었습니다. 정보가 정확하지 않을 수 있습니다."
    style: "warning"  # warning, info, note
  llm_assisted:
    enabled: true
    text: "이 게시글은 LLM의 도움을 받아 작성되었습니다."
    style: "info"
```

### 4.4 프롬프트 템플릿 예시 (templates/lecture_note.yaml)

```yaml
name: "렉쳐노트"
description: "수학 렉쳐노트 스타일로 작성"
system_prompt: |
  You are a mathematics educator writing lecture notes.
  Use rigorous notation, include proofs where appropriate,
  and provide intuitive explanations alongside formal definitions.
  Write in Korean with English mathematical terms.
user_prompt_template: |
  다음 내용을 바탕으로 렉쳐노트를 작성해주세요.
  ---
  {content}
```

---

## 5. 마일스톤

### M1: Hugo 사이트 기초

**목표**: Hugo 블로그가 GitHub Pages에 자동 배포되는 상태

| 태스크 | 요구사항 |
|--------|---------|
| Hugo 프로젝트 초기화 | FR-1.1 |
| Hugo Book 테마 submodule 추가 | FR-1.2 |
| GitHub Actions 배포 워크플로우 | FR-1.3 |
| 계층형 카테고리 구조 설계 | FR-2.1 |
| KaTeX 수식 렌더링 설정 | FR-2.2 |
| Giscus 댓글 연동 | FR-2.4 |
| .gitignore, .env.example 설정 | FR-1.4, FR-7.4 |
| pre-commit hook 설정 | FR-7.3 |

**완료 기준**: 샘플 게시글(수식 포함)이 GitHub Pages에 배포됨

---

### M2: Streamlit 기본 UI

**목표**: Streamlit으로 글 작성 → Hugo 마크다운 생성 → git push 가능

| 태스크 | 요구사항 |
|--------|---------|
| Streamlit 앱 기본 구조 | FR-3.1 |
| 마크다운 에디터 (직접 작성 모드) | FR-3.1 |
| Hugo 마크다운 생성기 (front matter 포함) | FR-3.1 |
| 카테고리 관리 UI | FR-3.6, FR-2.1 |
| 이미지 업로드 → 마크다운 삽입 | FR-3.5 |
| 수식 미리보기 | FR-2.2 |
| 작성 중 실시간 미리보기 | FR-3.8 |
| LLM 면책 조항 설정 UI | FR-3.7 |
| 설정 페이지 — 관심사 관리 | FR-6.4 |
| Git push 연동 | - |

**완료 기준**: Streamlit에서 글 작성 → 블로그에 게시됨

---

### M3: LLM 연동

**목표**: 페어 라이팅, 자동 생성 워크플로우 동작

| 태스크 | 요구사항 |
|--------|---------|
| LLMClient Protocol 정의 | FR-5.2 |
| Claude 클라이언트 구현 | FR-5.1 |
| OpenAI 클라이언트 구현 | FR-5.1 |
| Llama 클라이언트 구현 | FR-5.1 |
| 페어 라이팅 UI 워크플로우 | FR-3.2 |
| 자동 생성 UI 워크플로우 | FR-3.3 |
| API 키 관리 (환경변수 → .env) | FR-7.1 |
| LLM 프로바이더 선택 UI | FR-5.1 |
| 모델 선택 UI (프로바이더별) | FR-5.3 |

**완료 기준**: Streamlit에서 LLM 기반 글 작성 가능 (3가지 모드)

---

### M4: 소스 연동

**목표**: PDF, URL, arxiv 소스에서 LLM 기반 글 생성 가능

| 태스크 | 요구사항 |
|--------|---------|
| PDF 파서 (텍스트 + 이미지 추출) | FR-3.4, FR-3.5 |
| PDF 범위 지정 기능 | FR-3.4 |
| PDF 이미지 선택 UI | FR-3.5 |
| URL 크롤러 | FR-3.3 |
| arxiv 클라이언트 | FR-3.3 |
| 복수 소스 입력 UI + 소스 병합 로직 | FR-3.9 |
| 토큰 카운팅 + 자동 분기 | FR-5.4 |
| Map-Reduce 청킹 | FR-5.5 |
| Map/Reduce 모델 분리 설정 | FR-5.6 |
| 청크 병렬 처리 (asyncio) | FR-5.7 |

**완료 기준**: 복수 소스(PDF 2개 + URL)를 입력하여 글 자동 생성 가능

---

### M5: 템플릿 시스템

**목표**: 프롬프트 템플릿을 관리하고 글 작성에 적용 가능

| 태스크 | 요구사항 |
|--------|---------|
| 템플릿 YAML 스키마 정의 | FR-4.2 |
| 템플릿 CRUD UI | FR-4.1 |
| 글 작성 시 템플릿 선택 연동 | FR-4.3 |
| 기본 템플릿 세트 제공 (summary, 칼럼, 렉쳐노트) | FR-4.1 |
| 스타일 레퍼런스 등록/관리 UI (PDF, MD, TXT, URL) | FR-4.4 |
| 글 작성 시 스타일 레퍼런스 선택 연동 | FR-4.4 |

**완료 기준**: 템플릿 + 스타일 레퍼런스를 조합하여 원하는 문체/형식의 글 생성 가능

---

### M6: 외부 데이터 & 리포트

**목표**: 외부 데이터를 fetch하여 LLM 분석 리포트 생성

| 태스크 | 요구사항 |
|--------|---------|
| DataFetcher Protocol 정의 | FR-6.1 |
| FRED Fetcher 구현 | FR-6.1 |
| yfinance Fetcher 구현 | FR-6.1 |
| arxiv Fetcher 구현 | FR-6.1 |
| 리포트 생성 UI (데이터 선택 → LLM 분석) | FR-6.2 |

**완료 기준**: FRED 데이터 기반 경제 리포트 자동 생성 가능

---

### M7: 자동화

**목표**: 주기적 컨텐츠 자동 생성 및 PR 기반 게시

| 태스크 | 요구사항 |
|--------|---------|
| arxiv 일일 다이제스트 스크립트 | FR-6.3 |
| 2단계 필터링 (키워드 → LLM) | FR-6.3 |
| 논문 중복 방지 (arxiv_seen.json) | FR-6.6 |
| GitHub Actions cron 워크플로우 | FR-6.5 |
| PR 자동 생성 | FR-6.5 |
| 자동 포스팅 설정 UI | FR-6.5 |

**완료 기준**: 매일 아침 관심 분야 arxiv 논문 요약 PR이 자동 생성됨

---

### M8: 최적화 & 수익화

**목표**: 블로그 최적화 및 AdSense 연계

| 태스크 | 요구사항 |
|--------|---------|
| Google AdSense 연계 | - |
| SEO 최적화 (메타 태그, sitemap, robots.txt) | - |
| 성능 튜닝 (빌드 속도, 페이지 로딩) | - |
| Hugo 로컬 미리보기 연동 | FR-2.4 |

**완료 기준**: AdSense 승인 및 광고 표시, Lighthouse 성능 점수 90+

---

## 6. 개발 환경

### 6.1 문서 체계

| 문서 | 용도 |
|------|------|
| `PRD.md` | 제품 요구사항 (본 문서) |
| `TRD.md` | 기술 설계 (아키텍처 상세, API 설계, 데이터 모델) |
| `TASKS.md` | 마일스톤별 세부 태스크 체크리스트 |
| `CLAUDE.md` | Claude Code 프로젝트 컨텍스트 (코딩 컨벤션, 프로젝트 구조, 주요 결정사항) |
| `MANUAL.md` | 사용자 매뉴얼 (설치, 설정, Streamlit UI 사용법, 자동화 설정, 트러블슈팅) |

### 6.2 개발 원칙

- **Core/UI 분리**: 핵심 로직은 `core/` 패키지에, Streamlit은 `ui/`에서 core를 호출만 함
- **Protocol 기반 추상화**: LLMClient, DataFetcher 등 인터페이스를 Protocol로 정의
- **설정 외부화**: 하드코딩 금지, 모든 설정은 YAML/환경변수로 관리
- **점진적 구축**: M1→M8 순서로 각 마일스톤이 독립적으로 동작 가능한 상태 유지

---

## 7. 비기능 요구사항

| 항목 | 요구사항 |
|------|---------|
| 보안 | API 키가 절대 git에 커밋되지 않아야 함 |
| 비용 | Map 단계에 경량 모델 사용으로 LLM API 비용 최적화 |
| 확장성 | 새로운 LLM 프로바이더, Fetcher, 템플릿을 쉽게 추가 가능 |
| 사용성 | Streamlit UI를 통해 비개발자도 글 작성 가능 |

---

## 부록: 주요 설계 결정 기록

| 결정 | 선택 | 근거 |
|------|------|------|
| 테마 관리 | git submodule | Hugo 생태계 표준, 테마 업데이트 용이 |
| 외부 데이터 수집 | function 기반 | MCP 서버는 불필요한 오버헤드, Streamlit/Actions에서 직접 호출하는 구조 |
| 긴 문서 처리 | Map-Reduce | 토큰 카운팅 기반 자동 분기, 프로바이더별 컨텍스트 한도 대응 |
| 논문 중복 관리 | JSON 파일 | DB 불필요 (연간 수만 건 수준), git으로 상태 관리 |
| 자동 포스팅 | GitHub Actions cron + PR | 별도 인프라 불필요, PR로 안전장치 확보 |
| 템플릿 vs Claude Skills | 자체 템플릿 시스템 | API 직접 호출 구조이므로 Skills 불필요, 프로바이더 무관하게 적용 가능 |
| LLM 면책 조항 | front matter 플래그 + Hugo 레이아웃 | 템플릿에 넣으면 중복 관리 필요, 글 작성 모드에 따라 자동 삽입이 합리적 |
| 댓글 시스템 | Giscus | GitHub Discussions 기반으로 별도 인프라 불필요, GitHub 계정으로 댓글 가능 |
