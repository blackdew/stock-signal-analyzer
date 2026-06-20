# AGENTS.md

이 파일은 Codex 및 개발 에이전트가 이 저장소의 코드를 다룰 때 참고하는 아키텍처 가이드이자 상태 명세입니다.

## 프로젝트 개요

**섹터 순환 투자 전략 분석 시스템 (Sector Rotation Investment Analyzer)**
한국 주식 시장의 섹터별 투자 기회를 분석하고 루브릭 기반 점수로 투자 등급을 산출하는 Python 애플리케이션 및 React 기반 웹 대시보드입니다.

### 현재 상태
- **Phase 0 완료**: 기본 인프라 구축 (config, fetcher, cache, rubric V2)
- **Phase 1 완료**: 데이터 에이전트 (MarketDataAgent, FundamentalAgent, NewsAgent)
- **Phase 2 완료**: 분석 에이전트 (StockAnalyzer, SectorAnalyzer, RankingAgent)
- **Phase 4 완료**: 리포트 에이전d트 (StockReportAgent, SectorReportAgent, SummaryAgent)
- **Phase 5 완료**: Orchestrator 및 CLI (main.py)
- **Phase 6 완료**: Web API 및 React 프론트엔드 연동 (FastAPI + Vite)
- **Phase 7 완료**: 알고리즘 V3 튜닝 (거래대금 가중치, 결측치 리스케일, 동일 섹터 2개 제한, 가격 가이드 및 로컬 Codex fallback 지원)

---

## 실행 및 테스트 가이드

### 의존성 설치
```bash
# uv 패키지 매니저 사용
uv sync
```

### 모듈 테스트 및 자가 진단
```bash
# config 모듈 테스트
uv run python -c "from src.core.config import SECTORS, RUBRIC_WEIGHTS; print(SECTORS)"

# fetcher 모듈 테스트
uv run python -c "from src.data.fetcher import StockDataFetcher; f = StockDataFetcher(); print(f.get_all_sectors())"

# cache 모듈 테스트
uv run python -c "from src.data.cache import CacheManager; c = CacheManager(); print(c.get_stats())"

# rubric 모듈 테스트
uv run python -c "from src.core.rubric import RubricEngine; r = RubricEngine(); print(r.weights)"

# data agents 테스트
uv run python -c "from src.agents.data import MarketDataAgent; print('MarketDataAgent OK')"

# analysis agents 테스트
uv run python -c "from src.agents.analysis import StockAnalyzer, SectorAnalyzer, RankingAgent; print('Analysis Agents OK')"

# report agents 테스트
uv run python -c "from src.agents.report import StockReportAgent, SectorReportAgent, SummaryAgent; print('Report Agents OK')"
```

### 전체 유닛 테스트 구동 (테스트 속도 최적화 완료)
```bash
# tests/core 및 tests/agents 의 369개 테스트를 4초 내에 고속 실행
uv run pytest tests/core tests/agents
```

### 메인 실행 및 서버 구동
```bash
# 일간 리포트 생성 (기본값)
uv run python main.py

# 일간 리포트 (명시적)
uv run python main.py --daily

# 주간 섹터 리포트 생성
uv run python main.py --weekly

# 섹터 분석만 수행
uv run python main.py --sector-only

# 캐시 없이 상세 로그
uv run python main.py --no-cache -v

# 데이터 품질 기준 미달 시 실행 중단 (strict 모드)
uv run python main.py --strict

# API 서버 실행 (기본 포트: 8000)
uv run python main.py --web

# 커스텀 포트로 API 서버 실행
uv run python main.py --web --port 8080

# 커스텀 호스트로 API 서버 실행
uv run python main.py --web --host 127.0.0.1 --port 3000

# 도움말 출력
uv run python main.py --help
```

### 알고리즘 성과 비교 백테스트 구동
```bash
uv run python scripts/compare_recommendation_algorithms.py
```

### 통합 실행 (백엔드 + 프론트엔드)
```bash
# 프론트엔드 빌드 및 배포
./scripts/build_frontend.sh

# 웹 서버 실행 (백엔드 API + 프론트엔드)
uv run python main.py --web
# 브라우저: http://localhost:8000
```

### 개발 모드 (Hot Reload)
개발 시에는 백엔드와 프론트엔드를 별도 터미널에서 실행합니다:
```bash
# 터미널 1: 백엔드 API 서버
uv run python main.py --web

# 터미널 2: 프론트엔드 개발 서버 (Hot Reload)
cd poc-web && npm run dev -- --port 3002
# 브라우저: http://localhost:3002
```

---

## 프로젝트 구조

```
trading/
├── AGENTS.md                    # 이 파일
├── README.md                    # 프로젝트 소개 및 설치 가이드
├── pyproject.toml               # 의존성 정의
├── .env.example                 # 환경 변수 예시
│
├── scripts/                     # 유틸리티 스크립트
│   ├── performance_test.py      # 성능 테스트
│   ├── test_report_generation.py # 리포트 생성 테스트
│   ├── build_frontend.sh        # 프론트엔드 빌드 및 배포 스크립트
│   └── compare_recommendation_algorithms.py # 개선 알고리즘 비교 성과 검증 스크립트
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                    # 핵심 설정 및 엔진
│   │   ├── __init__.py
│   │   ├── config.py            # SECTORS(13개), RUBRIC_WEIGHTS(V3), INVESTMENT_GRADES
│   │   ├── rubric.py            # RubricEngine V3 (8개 핵심 카테고리)
│   │   ├── llm.py               # LLMAnalyzer - OpenAI 기반 상세 분석 생성 & Codex fallback 구현
│   │   ├── llm_scorer.py        # LLMScorer - LLM 기반 점수 산출 & Codex fallback 구현
│   │   ├── orchestrator.py      # Orchestrator - 전체 파이프라인 조율
│   │   ├── logging_config.py    # 로깅 설정, TaskLogHandler (SSE 로그 스트리밍)
│   │   └── prompts/             # LLM 프롬프트 템플릿
│   │
│   ├── data/                    # 데이터 수집 및 캐싱
│   │   ├── __init__.py
│   │   ├── fetcher.py           # StockDataFetcher
│   │   └── cache.py             # CacheManager
│   │
│   ├── agents/                  # 에이전트 기반 수집 및 분석
│   │   ├── base_agent.py        # BaseAgent (추상 클래스)
│   │   │
│   │   ├── data/                # 데이터 수집 에이전트
│   │   │   ├── market_data_agent.py    # 시장 데이터 및 20일 평균 거래대금 수집
│   │   │   ├── fundamental_agent.py    # 재무제표 수집
│   │   │   ├── news_agent.py           # 뉴스/센티먼트 수집
│   │   │   └── data_bundle.py          # StockDataBundle
│   │   │
│   │   ├── analysis/            # 분석 에이전트
│   │   │   ├── stock_analyzer.py       # 개별 종목 평가 및 ATR 가격 가이드 계산
│   │   │   ├── sector_analyzer.py      # 섹터 시가총액 가중 평균
│   │   │   ├── ranking_agent.py        # V3 보정 랭킹 스코어링 및 섹터 쏠림(동일 섹터 최대 2개) 가드
│   │   │   └── data_quality.py         # 데이터 품질 검증
│   │   │
│   │   └── report/              # 리포트 에이전트
│   │       ├── stock_report_agent.py   # 개별 종목 마크다운 리포트 (매매 가이드 추가)
│   │       ├── sector_report_agent.py  # 섹터 분석 마크다운 리포트
│   │       ├── summary_agent.py        # 종합 리포트 및 JSON 데이터
│   │       └── weekly_sector_report_agent.py  # 주간 섹터 분석 리포트
│   │
│   ├── web/                     # Web API (FastAPI)
│   │   ├── app.py               # FastAPI 앱 생성, CORS 설정 (3002~3005 허용)
│   │   ├── routes/              # API 라우터 (sectors/flow 동적 매칭 순서 교정 완료)
│   │
│   └── output/                  # 출력 디렉토리
│
├── tests/                       # 테스트 (369개)
│   ├── core/                    # rubric V1, V2, V3 테스트 및 가격 가이드/이중 리스케일링 검증
│   ├── agents/
│   │   ├── data/                # 데이터 에이전트 테스트
│   │   └── analysis/            # 분석 에이전트 테스트 (V3 랭킹 및 섹터 쏠림 가드 검증)
│
└── poc-web/                     # 프론트엔드 대시보드 (Vite + React)
    ├── App.tsx                  # 메인 대시보드 및 히스토리 선택 TypeError 복구 완료
    ├── components/              # React 차트, RRG Scatter 차트 및 카드 보드 컴포넌트
    └── services/
        ├── apiService.ts        # 백엔드 API 연동 (nullable 밸류 에러 복구 완료)
        └── geminiService.ts     # Gemini API 연동 (채팅 기능)
```
