# whi-blog

Hugo 정적 사이트 기반의 기술 블로그 엔진. Streamlit UI를 통한 글 작성 환경과 LLM 기반 컨텐츠 파이프라인을 제공한다.

## Features

- Hugo + GitHub Pages 자동 배포
- Streamlit CMS UI (직접 작성 / 페어 라이팅 / 자동 생성)
- 멀티 LLM 지원 (Claude, OpenAI, Llama)
- PDF, URL, arxiv 소스 연동
- Map-Reduce 기반 긴 문서 처리
- 프롬프트 템플릿 & 스타일 레퍼런스 시스템
- 외부 데이터 리포트 (FRED, yfinance)
- arxiv 일일 다이제스트 자동 포스팅

## Quick Start

```bash
# 의존성 설치
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# Streamlit 앱 실행
streamlit run ui/app.py

# Hugo 로컬 서버
cd hugo-site && hugo server -D
```

## Project Structure

```
whi-blog/
├── core/           # 핵심 Python 라이브러리 (UI 의존성 없음)
├── ui/             # Streamlit 앱
├── config/         # 설정 파일 (YAML)
├── templates/      # 프롬프트 템플릿
├── references/     # 스타일 레퍼런스
├── hugo-site/      # Hugo 프로젝트
├── scripts/        # CLI 스크립트
└── tests/          # 테스트
```

## Tech Stack

- **Static Site**: Hugo + hugo-book theme
- **CMS UI**: Streamlit
- **LLM**: Claude (Anthropic), OpenAI, Llama (Ollama)
- **CI/CD**: GitHub Actions
- **Hosting**: GitHub Pages

## License

MIT
