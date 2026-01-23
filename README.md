# Stock Signal Analyzer

**섹터 순환 투자 전략 분석 시스템**

한국 주식 시장의 섹터별 투자 기회를 분석하고, 루브릭 기반 점수로 투자 등급을 산출하는 Python 애플리케이션입니다.

## 현재 상태

| 단계 | 상태 | 설명 |
|------|------|------|
| Phase 0 | 완료 | 기본 인프라 (config, fetcher, cache, rubric V2) |
| Phase 1 | 완료 | 데이터 에이전트 (MarketDataAgent, FundamentalAgent, NewsAgent) |
| Phase 2 | 완료 | 분석 에이전트 (StockAnalyzer, SectorAnalyzer, RankingAgent) |
| Phase 4 | 완료 | 리포트 에이전트 (StockReportAgent, SectorReportAgent, SummaryAgent) |
| Phase 5 | 완료 | Orchestrator 및 CLI (main.py) |
| Phase 6 | 완료 | Web API (FastAPI 기반 REST API) |

### 테스트 현황
- **총 279개 테스트**
  - core (rubric V1, V2): 166개
  - agents/data: 64개
  - agents/analysis: 49개

## 기술 스택

- **Python 3.12+**
- **네이버 금융 크롤링**: 한국 주식 데이터 수집
- **pandas / pandas-ta**: 데이터 분석 및 기술적 지표
- **FastAPI / uvicorn**: REST API 서버
- **uv**: 패키지 관리 및 실행

## 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd trading

# 의존성 설치 (uv 사용)
uv sync
```

### 2. 모듈 동작 확인

```bash
# 설정 확인
uv run python -c "from src.core.config import SECTORS; print(SECTORS)"

# 데이터 수집 확인
uv run python -c "from src.data.fetcher import StockDataFetcher; f = StockDataFetcher(); print(f.get_all_sectors())"

# 루브릭 엔진 확인
uv run python -c "from src.core.rubric import RubricEngine; print(RubricEngine().weights)"
```

### 3. 실행

```bash
# CLI: 일간 리포트 생성
uv run python main.py --daily

# CLI: 주간 리포트 생성
uv run python main.py --weekly

# API 서버만 실행
uv run python main.py --web
# API 문서: http://localhost:8000/docs
```

### 4. 통합 실행 (백엔드 + 프론트엔드)

```bash
# 프론트엔드 빌드 및 배포
./scripts/build_frontend.sh

# 웹 서버 실행 (백엔드 API + 프론트엔드)
uv run python main.py --web
# 브라우저: http://localhost:8000
```

### 5. 개발 모드 (Hot Reload)

개발 시에는 백엔드와 프론트엔드를 별도 터미널에서 실행합니다:

```bash
# 터미널 1: 백엔드 API 서버
uv run python main.py --web

# 터미널 2: 프론트엔드 개발 서버 (Hot Reload)
cd poc-web && npm run dev
# 브라우저: http://localhost:3000
```

## 핵심 기능

### 섹터 기반 분석
- 11개 섹터 지원: 반도체, 조선, 방산, 원전, 전력기기, 바이오, 로봇, 자동차, 신재생에너지, 지주, 뷰티
- 각 섹터별 5개 대표 종목 분석
- 섹터 확장 용이 (config.py에서 관리)

### 루브릭 평가 시스템 V2 (100점)
- 기술적 분석 (25점): 추세, RSI, 지지/저항, MACD, ADX
- 수급 분석 (20점): 외국인, 기관, 거래대금
- 펀더멘털 분석 (20점): PER, PBR, ROE, 성장률, 부채비율
- 시장 환경 (15점): 뉴스, 섹터모멘텀, 애널리스트
- 리스크 평가 (10점): 변동성, 베타, 하방리스크
- 상대 강도 (10점): 섹터내순위, 시장대비알파

### 투자 등급 산출
| 등급 | 점수 범위 |
|------|----------|
| Strong Buy | 80-100 |
| Buy | 60-79 |
| Hold | 40-59 |
| Sell | 20-39 |
| Strong Sell | 0-19 |

### 데이터 에이전트
- **MarketDataAgent**: 시장 데이터 (주가, 거래량, 기술적 지표)
- **FundamentalAgent**: 재무제표 (PER, PBR, ROE, 성장률)
- **NewsAgent**: 뉴스 센티먼트

### 분석 에이전트
- **StockAnalyzer**: 개별 종목 루브릭 점수 산출
- **SectorAnalyzer**: 섹터별 시가총액 가중 평균 점수
- **RankingAgent**: 4개 그룹 순위, 최종 18개 종목, Top 3 선정

### 리포트 에이전트
- **StockReportAgent**: 개별 종목 마크다운 리포트 생성
- **SectorReportAgent**: 섹터 분석 마크다운 리포트 생성
- **SummaryAgent**: 종합 리포트 및 JSON 데이터 생성
- **WeeklySectorReportAgent**: 주간 섹터 분석 리포트 생성

### Web API
- **FastAPI 기반 REST API**: 분석 결과 조회 및 실행
- **주요 엔드포인트**:
  - `GET /api/analysis/latest` - 최신 분석 결과
  - `GET /api/ranking` - Top 18, Top 5 순위
  - `GET /api/sectors` - 섹터 분석 결과
  - `GET /api/stocks` - 종목 분석 결과
  - `GET /api/stocks/{symbol}/history` - 일별 주가 히스토리
  - `GET /api/stocks/{symbol}/supply` - 외국인/기관 순매수 추이
  - `POST /api/analysis/run` - 분석 비동기 실행

## 프로젝트 구조

```
trading/
├── src/
│   ├── core/               # 설정 및 평가 엔진
│   │   ├── config.py       # SECTORS(11개), RUBRIC_WEIGHTS(V2)
│   │   ├── rubric.py       # RubricEngine V2 (6개 카테고리)
│   │   └── orchestrator.py # 전체 파이프라인 조율
│   ├── data/               # 데이터 수집 및 캐싱
│   │   ├── fetcher.py      # StockDataFetcher
│   │   └── cache.py        # CacheManager
│   └── agents/
│       ├── base_agent.py   # BaseAgent 추상 클래스
│       ├── data/           # 데이터 수집 에이전트
│       │   ├── market_data_agent.py
│       │   ├── fundamental_agent.py
│       │   └── news_agent.py
│       ├── analysis/       # 분석 에이전트
│       │   ├── stock_analyzer.py
│       │   ├── sector_analyzer.py
│       │   └── ranking_agent.py
│       └── report/         # 리포트 에이전트
│           ├── stock_report_agent.py
│           ├── sector_report_agent.py
│           ├── summary_agent.py
│           └── weekly_sector_report_agent.py
│   └── web/                # Web API (FastAPI)
│       ├── app.py          # FastAPI 앱 생성
│       ├── schemas.py      # Pydantic 스키마
│       └── routes/         # API 라우터
│           ├── analysis.py # 분석 API
│           ├── sectors.py  # 섹터 API
│           └── stocks.py   # 종목 API
├── tests/                  # 테스트 (279개)
├── docs/
│   └── architecture.md     # 아키텍처 문서
├── poc-web/                # 프론트엔드 PoC (Gemini AI Studio)
│   ├── index.tsx           # 메인 앱 엔트리
│   ├── types.ts            # TypeScript 타입 정의
│   ├── .env.example        # 환경 변수 예시
│   ├── components/         # React 컴포넌트
│   └── services/           # API 서비스
│       ├── apiService.ts   # 백엔드 API 연동
│       └── geminiService.ts# Gemini API 연동
├── CLAUDE.md               # Claude Code 가이드
└── pyproject.toml
```

## 문서

- [CLAUDE.md](./CLAUDE.md): 개발 가이드 및 모듈 상세 설명
- [docs/architecture.md](./docs/architecture.md): 아키텍처 설계

## 주의사항

이 앱은 투자 참고용이며, 실제 투자 결정은 본인의 판단에 따라야 합니다.
분석 결과는 과거 데이터 기반이므로 미래 수익을 보장하지 않습니다.

## 라이센스

MIT License
