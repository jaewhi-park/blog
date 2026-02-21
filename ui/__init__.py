"""Streamlit UI package."""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (core 패키지 import 지원)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
