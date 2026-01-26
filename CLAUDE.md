# CLAUDE.md

이 파일은 Claude Code가 이 저장소의 코드를 다룰 때 참고하는 가이드입니다.

## 프로젝트 개요

**섹터 순환 투자 전략 분석 시스템** - 한국 주식 시장의 섹터별 투자 기회를 분석하고 루브릭 기반 점수로 투자 등급을 산출하는 Python 애플리케이션입니다.

### 현재 상태
- **Phase 0 완료**: 기본 인프라 구축 (config, fetcher, cache, rubric V2)
- **Phase 1 완료**: 데이터 에이전트 (MarketDataAgent, FundamentalAgent, NewsAgent)
- **Phase 2 완료**: 분석 에이전트 (StockAnalyzer, SectorAnalyzer, RankingAgent)
- **Phase 4 완료**: 리포트 에이전트 (StockReportAgent, SectorReportAgent, SummaryAgent)
- **Phase 5 완료**: Orchestrator 및 CLI (main.py)
- **Phase 6 완료**: Web API (FastAPI 기반 REST API)

## 실행 방법

### 의존성 설치
```bash
# uv 패키지 매니저 사용
uv sync
```

### 모듈 테스트
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

### 메인 실행
```bash
# 일간 리포트 생성 (기본값)
uv run python main.py

# 일간 리포트 (명시적)
uv run python main.py --daily

# 주간 섹터 리포트 생성
uv run python main.py --weekly

# 섹터 분석만
uv run python main.py --sector-only

# 캐시 없이 상세 로그
uv run python main.py --no-cache -v

# 데이터 품질 기준 미달 시 실행 중단 (strict 모드)
uv run python main.py --strict

# API 서버 실행
uv run python main.py --web

# 커스텀 포트로 API 서버 실행
uv run python main.py --web --port 8080

# 커스텀 호스트로 API 서버 실행
uv run python main.py --web --host 127.0.0.1 --port 3000

# 도움말
uv run python main.py --help
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
cd poc-web && npm run dev
# 브라우저: http://localhost:3000
```

### 테스트 스크립트
```bash
# 리포트 생성 테스트 (날짜별 폴더 구조 검증)
uv run scripts/test_report_generation.py
```

## 프로젝트 구조

```
trading/
├── CLAUDE.md                    # 이 파일
├── README.md                    # 프로젝트 소개
├── pyproject.toml               # 의존성 정의
├── .env.example                 # 환경 변수 예시 (API_HOST, API_PORT, OPENDART_API_KEY, OPENAI_API_KEY)
│
├── scripts/                     # 유틸리티 스크립트
│   ├── performance_test.py      # 성능 테스트
│   ├── test_report_generation.py # 리포트 생성 테스트
│   └── build_frontend.sh        # 프론트엔드 빌드 및 배포 스크립트
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                    # 핵심 설정 및 엔진
│   │   ├── __init__.py
│   │   ├── config.py            # SECTORS(13개), RUBRIC_WEIGHTS(V2), INVESTMENT_GRADES
│   │   ├── rubric.py            # RubricEngine V2 (6개 카테고리)
│   │   ├── llm.py               # LLMAnalyzer - OpenAI 기반 상세 분석 생성
│   │   ├── llm_scorer.py        # LLMScorer - LLM 기반 점수 산출 (RubricEngine 대체)
│   │   ├── orchestrator.py      # Orchestrator - 전체 파이프라인 조율
│   │   ├── logging_config.py    # 로깅 설정, TaskLogHandler (SSE 로그 스트리밍)
│   │   └── prompts/             # LLM 프롬프트 템플릿
│   │       ├── __init__.py
│   │       ├── stock_analysis.py     # 개별 종목 분석 프롬프트
│   │       ├── sector_analysis.py    # 섹터 분석 프롬프트
│   │       └── schemas.py            # JSON 출력 스키마 및 검증
│   │
│   ├── data/                    # 데이터 수집 및 캐싱
│   │   ├── __init__.py
│   │   ├── fetcher.py           # StockDataFetcher, StockInfo, StockData
│   │   └── cache.py             # CacheManager, CacheTTL
│   │
│   ├── agents/                  # 에이전트 기반 수집 및 분석
│   │   ├── __init__.py
│   │   ├── base_agent.py        # BaseAgent (추상 클래스)
│   │   │
│   │   ├── data/                # 데이터 수집 에이전트
│   │   │   ├── __init__.py
│   │   │   ├── market_data_agent.py    # 시장 데이터 수집
│   │   │   ├── fundamental_agent.py    # 재무제표 수집
│   │   │   ├── news_agent.py           # 뉴스/센티먼트 수집
│   │   │   └── data_bundle.py          # StockDataBundle - LLM 분석용 데이터 통합
│   │   │
│   │   ├── analysis/            # 분석 에이전트
│   │   │   ├── __init__.py
│   │   │   ├── stock_analyzer.py       # 개별 종목 점수 (LLMScorer 우선, RubricEngine 폴백)
│   │   │   ├── sector_analyzer.py      # 섹터 시가총액 가중 평균
│   │   │   ├── ranking_agent.py        # 4개 그룹 순위, 최종 18개, Top 5
│   │   │   └── data_quality.py         # 데이터 품질 검증
│   │   │
│   │   └── report/              # 리포트 에이전트
│   │       ├── __init__.py
│   │       ├── stock_report_agent.py   # 개별 종목 마크다운 리포트
│   │       ├── sector_report_agent.py  # 섹터 분석 마크다운 리포트
│   │       ├── summary_agent.py        # 종합 리포트 및 JSON 데이터
│   │       └── weekly_sector_report_agent.py  # 주간 섹터 분석 리포트
│   │
│   ├── web/                     # Web API (FastAPI)
│   │   ├── __init__.py
│   │   ├── app.py               # FastAPI 앱 생성, CORS 설정, 정적 파일 서빙, AppState (태스크 로그 버퍼)
│   │   ├── schemas.py           # Pydantic 스키마 정의
│   │   ├── static/              # 프론트엔드 빌드 결과물 (build_frontend.sh로 생성)
│   │   └── routes/              # API 라우터
│   │       ├── __init__.py
│   │       ├── analysis.py      # 분석 실행/결과 조회 API, SSE 로그 스트리밍
│   │       ├── sectors.py       # 섹터 분석 API
│   │       └── stocks.py        # 종목 분석 API
│   │
│   └── output/                  # 출력 디렉토리
│       ├── data/
│       │   └── cache/           # 캐시 파일 저장
│       └── reports/             # 날짜별 리포트 폴더 (YYYY-MM-DD/)
│
├── output/                      # 실제 출력 디렉토리
│   ├── data/                    # JSON 데이터 저장
│   └── reports/
│       └── YYYY-MM-DD/          # 날짜별 리포트 폴더
│           ├── 01_sector_report.md   # 섹터 통합 리포트
│           ├── 02_stocks/            # 종목별 리포트
│           │   ├── 005930_삼성전자.md
│           │   └── ...
│           └── 03_final_report.md    # 최종 종합 리포트
│
├── tests/                       # 테스트 (279개)
│   ├── core/                    # rubric V1, V2 테스트 (166개)
│   ├── agents/
│   │   ├── data/                # 데이터 에이전트 테스트 (64개)
│   │   └── analysis/            # 분석 에이전트 테스트 (49개)
│
├── docs/
│   └── architecture.md          # 아키텍처 설명
│
└── poc-web/                     # 프론트엔드 PoC (Gemini AI Studio)
    ├── index.tsx                # 앱 엔트리 포인트
    ├── App.tsx                  # 메인 앱 컴포넌트 (라우팅, 상태 관리)
    ├── types.ts                 # TypeScript 타입 정의 (6개 루브릭 카테고리, finalTop5, final18, allSectors, 차트 데이터)
    ├── vite-env.d.ts            # Vite 환경 변수 타입 선언
    ├── .env.example             # 환경 변수 예시 (VITE_API_URL, GEMINI_API_KEY)
    ├── components/              # React 컴포넌트
    │   ├── StockCard.tsx        # 종목 카드
    │   ├── StockModal.tsx       # 종목 상세 모달 (차트 탭 포함)
    │   ├── RubricChart.tsx      # 루브릭 점수 차트
    │   ├── ChatSidebar.tsx      # 채팅 사이드바
    │   ├── SectorBarChart.tsx   # 섹터별 점수 바 차트
    │   ├── Skeleton.tsx         # 로딩 스켈레톤 UI
    │   ├── ErrorState.tsx       # 에러 상태 표시 컴포넌트
    │   ├── PriceChart.tsx       # 주가 캔들스틱 차트 (OHLCV)
    │   ├── SupplyChart.tsx      # 외국인/기관 순매수 차트
    │   └── PriceRangeIndicator.tsx  # 52주 고저 대비 현재가 위치 표시
    └── services/
        ├── apiService.ts        # Python 백엔드 API 연동 (분석 결과, 차트 데이터 조회)
        └── geminiService.ts     # Gemini API 연동 (채팅 기능)
```

## 핵심 모듈 설명

### src/core/config.py
프로젝트 전역 설정을 정의합니다.

```python
# 분석 대상 섹터 및 대표 종목 (13개 섹터)
SECTORS = {
    "반도체": ["005930", "000660", "042700", "403870", "058470", ...],
    "조선": ["010140", "009540", "042660", "010620", "329180", ...],
    "방산/우주": ["012450", "047810", "064350", "079550", "273640", ...],
    "전력인프라": ["034020", "267260", "298040", "010120", "051600", ...],
    "바이오": ["207940", "068270", "326030", "141080", "145020", ...],
    "로봇": ["336260", "108490", "090710", "309930", "950140", ...],
    "자동차": ["005380", "000270", "012330", "204320", "161390", ...],
    "신재생에너지": ["009830", "112610", "010060", "086520", "003670", ...],
    "지주": ["000810", "003550", "001040", "005490", "006400", ...],
    "뷰티": ["090430", "051900", "192820", "161890", "237880", ...],
    "금융": ["105560", "055550", "086790", "316140", "024110", ...],
    "푸드": ["097950", "271560", "004370", "280360", "005300", ...],
    "엔터": ["352820", "041510", "122870", "035900", "259960", ...],
}

# 루브릭 가중치 V2 (6개 카테고리, 100점 만점)
RUBRIC_WEIGHTS = {
    "technical": 25,          # 기술적 분석 (추세, RSI, 지지/저항, MACD, ADX)
    "supply": 20,             # 수급 분석 (외국인, 기관, 거래대금)
    "fundamental": 20,        # 펀더멘털 분석 (PER, PBR, ROE, 성장률, 부채비율)
    "market": 15,             # 시장 환경 분석 (뉴스, 섹터모멘텀, 애널리스트)
    "risk": 10,               # 리스크 평가 (변동성, 베타, 하방리스크)
    "relative_strength": 10,  # 상대 강도 (섹터내순위, 시장대비알파)
}

# 하위 호환성을 위한 기존 가중치 (V1)
RUBRIC_WEIGHTS_V1 = {
    "technical": 30,
    "supply": 25,
    "fundamental": 25,
    "market": 20,
}

# 투자 등급 기준
INVESTMENT_GRADES = {
    "Strong Buy": (80, 100),
    "Buy": (60, 79),
    "Hold": (40, 59),
    "Sell": (20, 39),
    "Strong Sell": (0, 19),
}
```

**유틸리티 함수:**
- `get_grade_from_score(score)`: 점수 -> 투자 등급
- `get_all_sector_symbols()`: 모든 섹터의 종목 코드
- `get_sector_by_symbol(symbol)`: 종목 코드 -> 섹터명

### src/data/fetcher.py
네이버 금융을 사용한 주식 데이터 수집.

```python
from src.data.fetcher import StockDataFetcher, StockInfo, StockData

fetcher = StockDataFetcher()

# 주가 데이터 가져오기
df = fetcher.fetch_stock_data("005930", "2024-01-01", "2024-12-31")

# 종목명 조회
name = fetcher.get_stock_name("005930")  # "삼성전자"

# 시가총액 상위 종목
top_stocks = fetcher.get_market_cap_rank(market="KOSPI", top_n=20)

# 섹터별 종목 조회
sector_stocks = fetcher.get_sector_stocks("반도체")

# 주가 + 기술적 지표
stock_data = fetcher.fetch_stock_data_with_info("005930", "2024-01-01", "2024-12-31")
```

**데이터 클래스:**
- `StockInfo`: 종목 기본 정보 (symbol, name, market_cap, sector)
- `StockData`: 주가 데이터 + 지표 (symbol, name, df, indicators)

### src/data/cache.py
JSON 파일 기반 캐싱 시스템.

```python
from src.data.cache import CacheManager, CacheTTL

cache = CacheManager()

# 캐시 저장
cache.set("market_cap_005930", data, ttl_hours=24)

# 캐시 조회
data = cache.get("market_cap_005930", max_age_hours=24)

# 패턴 매칭 삭제
cache.clear("market_cap_*")

# 통계 조회
stats = cache.get_stats()
```

**TTL 상수:**
- `CacheTTL.PRICE`: 4시간 (주가/거래량)
- `CacheTTL.MARKET_CAP`: 24시간 (시총 순위)
- `CacheTTL.SUPPLY`: 24시간 (수급 데이터)
- `CacheTTL.FUNDAMENTAL`: 168시간 (재무제표, 7일)

### src/core/rubric.py
루브릭 기반 투자 점수 산출 엔진 (V2).

```python
from src.core.rubric import RubricEngine, RubricResult

# V2 엔진 (기본값)
engine = RubricEngine(use_v2=True)

# V1 엔진 (하위 호환)
engine_v1 = RubricEngine(use_v2=False)

result = engine.calculate(
    symbol="005930",
    name="삼성전자",
    market_data=market_data,
    fundamental_data=fundamental_data,
    news_data=news_data,
    low_52w=50000,
    high_52w=80000,
    # V2 추가 파라미터
    atr_pct=3.5,
    beta=1.1,
    max_drawdown_pct=15.0,
    sector_rank=2,
    sector_total=10,
    stock_return_20d=5.0,
    market_return_20d=2.0,
)

print(f"총점: {result.total_score}, 등급: {result.grade}")
# 출력: 총점: 65.3, 등급: Buy
```

**평가 카테고리 V2 (100점 만점):**
- 기술적 분석 (25점): 추세(6) + RSI(6) + 지지/저항(6) + MACD(4) + ADX(3)
- 수급 분석 (20점): 외국인(8) + 기관(8) + 거래대금(4)
- 펀더멘털 분석 (20점): PER(4) + PBR(4) + ROE(4) + 성장률(5) + 부채비율(3)
- 시장 환경 (15점): 뉴스(7.5) + 섹터모멘텀(3.75) + 애널리스트(3.75)
- 리스크 평가 (10점): 변동성(4) + 베타(3) + 하방리스크(3)
- 상대 강도 (10점): 섹터내순위(5) + 시장대비알파(5)

**평가 카테고리 V1 (하위 호환, 100점 만점):**
- 기술적 분석 (30점): 추세(10) + RSI(10) + 지지/저항(10)
- 수급 분석 (25점): 외국인(10) + 기관(10) + 거래대금(5)
- 펀더멘털 분석 (25점): PER(10) + 성장률(10) + 부채비율(5)
- 시장 환경 (20점): 뉴스(10) + 섹터모멘텀(5) + 애널리스트(5)

### src/core/llm.py
LLM 기반 상세 분석 생성 모듈 (OpenAI GPT-4o-mini).

```python
from src.core.llm import LLMAnalyzer, LLMAnalysisResult

# LLM 분석기 초기화 (OPENAI_API_KEY 환경변수 필요)
analyzer = LLMAnalyzer()

# LLM 사용 가능 여부 확인
if analyzer.is_available():
    result = await analyzer.analyze(
        symbol="005930",
        name="삼성전자",
        sector="반도체",
        market_cap=3000000,
        total_score=72.5,
        grade="Buy",
        technical_score=20.1,
        supply_score=17.4,
        fundamental_score=17.5,
        market_score=10.5,
        risk_score=7.0,
        relative_strength_score=0.0,
        technical_details={...},
        fundamental_details={...},
        strengths=["기술적 지표 상승 추세", "수급 양호"],
        weaknesses=["리스크 높음"],
    )

    print(result.summary)  # "AI 메모리 반도체(HBM) 시장의 절대적 지배력..."
    print(result.financial_analysis)  # 재무 & 밸류에이션 분석 (마크다운)
    print(result.technical_analysis)  # 기술적 & 차트 분석 (마크다운)
    print(result.comprehensive_analysis)  # 종합 투자 의견 (마크다운)
```

**LLMAnalysisResult 필드:**
- `summary`: 핵심 요약 (1-2문장)
- `financial_analysis`: 재무 & 밸류에이션 분석 (마크다운)
- `technical_analysis`: 기술적 & 차트 분석 (마크다운)
- `market_sentiment`: 뉴스 & 시장 센티먼트 (마크다운)
- `comprehensive_analysis`: 종합 투자 의견 (마크다운)
- `investment_thesis`: 투자 포인트 리스트 (3-5개)
- `risks`: 리스크 요인 리스트 (2-4개)

**섹터별 컨텍스트 지원:**
13개 섹터(반도체, 조선, 방산/우주, 전력인프라, 바이오, 로봇, 자동차, 신재생에너지, 지주, 뷰티, 금융, 푸드, 엔터)에 대한 전문적인 컨텍스트 프롬프트 제공.

### src/core/llm_scorer.py
LLM 기반 점수 산출기. 기존 RubricEngine을 대체하여 LLM이 직접 점수와 분석을 생성합니다.

```python
from src.core.llm_scorer import LLMScorer, LLMScoreResult, SectorLLMResult

# LLM 스코어러 초기화 (OPENAI_API_KEY 환경변수 필요)
scorer = LLMScorer()

# LLM 사용 가능 여부 확인
if scorer.is_available():
    # 개별 종목 분석
    result = await scorer.analyze_stock(data_bundle)

    print(result.total_score)  # 75.3
    print(result.grade)        # "Buy"
    print(result.summary)      # "AI 반도체 슈퍼사이클의 최대 수혜주"

    # 섹터 분석
    sector_result = await scorer.analyze_sector(
        sector_name="반도체",
        weighted_score=72.5,
        simple_score=68.3,
        technical_score=18.5,
        supply_score=16.2,
        fundamental_score=15.8,
        market_score=12.0,
        stock_count=5,
        total_market_cap=500000,
        top_stocks=[...],
        supply_data={...},
    )
```

**LLMScoreResult 필드:**
- `symbol`, `name`: 종목 코드, 종목명
- 점수 (6개 카테고리): `technical_score` (0-25), `supply_score` (0-20), `fundamental_score` (0-20), `market_score` (0-15), `risk_score` (0-10), `relative_strength_score` (0-10)
- `total_score`: 총점 (0-100)
- `grade`: 투자 등급 (Strong Buy/Buy/Hold/Sell/Strong Sell)
- 분석 텍스트: `summary`, `financial_analysis`, `technical_analysis`, `market_sentiment`, `comprehensive_analysis`
- `investment_thesis`: 투자 포인트 리스트
- `risks`: 리스크 요인 리스트
- `category_reasoning`: 카테고리별 판단 근거
- `is_fallback`: LLM 실패로 인한 기본값 여부
- `fallback_reason`: 폴백 사유 (API 할당량 초과, 인증 실패 등)

**SectorLLMResult 필드:**
- `sector_name`: 섹터명
- `reasoning`: 섹터 분석 요약
- `outlook`: 향후 전망
- `key_drivers`: 핵심 모멘텀 리스트
- `investment_strategy`: 투자 전략

### src/core/prompts/
LLM 분석을 위한 프롬프트 템플릿 모듈.

```python
from src.core.prompts import (
    STOCK_ANALYSIS_PROMPT,
    build_stock_analysis_prompt,
    SECTOR_ANALYSIS_PROMPT,
    build_sector_analysis_prompt,
    STOCK_SCORE_SCHEMA,
    SECTOR_SCORE_SCHEMA,
)

# 종목 분석 프롬프트 생성
prompt = build_stock_analysis_prompt(data_bundle.to_prompt_context())

# 섹터 분석 프롬프트 생성
prompt = build_sector_analysis_prompt(
    sector_name="반도체",
    sector_context="메모리/시스템 반도체, AI 가속기 포함",
    stock_count=5,
    ...
)
```

**프롬프트 구성:**
- `stock_analysis.py`: 개별 종목 분석 프롬프트 (6개 카테고리별 상세 평가 기준표 포함)
- `sector_analysis.py`: 섹터 분석 프롬프트 (수급 현황, 상위 종목 분석)
- `schemas.py`: JSON 출력 스키마 정의 및 응답 검증 함수 (`validate_stock_score()`, `validate_sector_score()`)

### src/agents/data/data_bundle.py
LLM 분석을 위한 종합 데이터 번들. 수집된 모든 데이터를 LLM 프롬프트에 적합한 형태로 통합합니다.

```python
from src.agents.data.data_bundle import StockDataBundle

# 수집된 데이터로부터 번들 생성
bundle = StockDataBundle.from_collected_data(
    symbol="005930",
    name="삼성전자",
    sector="반도체",
    market_cap=3000000,
    market_data=market_data,       # MarketData 객체
    fundamental_data=fundamental,  # FundamentalData 객체
    news_data=news,               # NewsData 객체
)

# LLM 프롬프트용 컨텍스트 문자열 생성
context = bundle.to_prompt_context()
# 출력:
# ## 종목 정보
# - 종목명: 삼성전자
# - 종목코드: 005930
# - 섹터: 반도체
# ...

# 딕셔너리로 변환
data_dict = bundle.to_dict()
```

**StockDataBundle 필드:**
- `symbol`, `name`, `sector`, `market_cap`: 기본 정보
- `price_data`: 현재가, 전일대비, 52주 고저, 52주 내 위치
- `technical_indicators`: MA20, MA60, RSI, MACD, ADX, ATR%, Beta, 20일 수익률
- `supply_data`: 외국인/기관 5일 순매수, 연속 순매수 일수, 거래대금
- `fundamental_data`: PER, PBR, ROE, 영업이익률, 성장률, 부채비율
- `news_data`: 뉴스 건수, 센티먼트 비율, 주요 헤드라인
- `sector_context`: 섹터별 분석 컨텍스트

### src/agents/base_agent.py
모든 에이전트의 추상 기반 클래스.

```python
from src.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    async def collect(self, symbols: list[str]) -> dict[str, Any]:
        # 구현
        pass

agent = MyAgent()
data = await agent.collect(["005930", "000660"])
```

**제공 기능:**
- 캐시 통합 (`self.cache`)
- 로깅 (`self._log_info()`, `self._log_error()` 등)
- 캐시-또는-페치 유틸리티 (`_get_cached_or_fetch()`)

### src/agents/data/
데이터 수집 에이전트 모듈.

- **MarketDataAgent**: 시장 데이터 수집 (주가, 거래량, 기술적 지표)
- **FundamentalAgent**: 재무제표 수집 (PER, PBR, ROE, 성장률, 부채비율)
- **NewsAgent**: 뉴스 및 센티먼트 분석
- **StockDataBundle**: LLM 분석을 위한 종합 데이터 번들

### src/agents/analysis/
분석 에이전트 모듈.

```python
from src.agents.analysis import StockAnalyzer, SectorAnalyzer, RankingAgent

# 개별 종목 분석
stock_analyzer = StockAnalyzer()
results = await stock_analyzer.analyze_symbols(["005930", "000660"])
kospi_results = await stock_analyzer.analyze_kospi_top(20)

# 섹터 분석 (시가총액 가중 평균)
sector_analyzer = SectorAnalyzer()
sector_results = await sector_analyzer.analyze()
top3_sectors = sector_analyzer.get_top_sectors(sector_results, top_n=3)

# 최종 순위 산정
ranking_agent = RankingAgent()
result = await ranking_agent.rank()
print(result.final_18)   # 최종 18개 종목
print(result.final_top5) # Top 5 종목
```

- **StockAnalyzer**: 개별 종목 점수 산출
  - 4개 그룹별 분석: KOSPI Top10, KOSPI 11~20, KOSDAQ Top10, 섹터별
  - LLMScorer 우선, RubricEngine 폴백 방식
  - `use_llm` 옵션으로 LLM 사용 여부 제어
  - `is_fallback`, `fallback_reason` 필드로 LLM 실패 추적

- **SectorAnalyzer**: 섹터별 점수 산출
  - 시가총액 가중 평균 점수 계산
  - 상위 섹터 선정

- **RankingAgent**: 최종 순위 산정
  - 4개 그룹에서 각 3개 종목 선정 (KOSPI 9개 + KOSDAQ 3개 + 섹터 9개)
  - 중복 제거 후 최종 18개 종목 집계
  - Top 5 선정 (가중치: 총점 70%, 수급 15%, 성장성 15%)

- **DataQualityValidator**: 데이터 품질 검증
  - 필수 항목: 현재가, 시가총액, 기술적 지표(MA20/RSI), 거래량
  - 권장 항목: 펀더멘털(PER/PBR/ROE), 52주 고저
  - 품질 점수 산출 (100점 만점)
  - `--strict` 모드에서 필수 항목 누락 시 실행 중단

### src/agents/report/
리포트 생성 에이전트 모듈.

```python
from src.agents.report import StockReportAgent, SectorReportAgent, SummaryAgent, WeeklySectorReportAgent
from pathlib import Path

# 날짜별 출력 디렉토리 설정
date_report_dir = Path("output/reports/2025-01-18")

# 섹터 통합 리포트 생성 (01_sector_report.md)
sector_report_agent = SectorReportAgent(output_dir=date_report_dir)
sector_path = await sector_report_agent.generate_unified_report(sector_results)

# 개별 종목 리포트 생성 (02_stocks/)
stocks_dir = date_report_dir / "02_stocks"
stock_report_agent = StockReportAgent(output_dir=stocks_dir)
stock_paths = await stock_report_agent.generate_reports(stock_results)

# 종합 리포트 생성 (03_final_report.md)
summary_agent = SummaryAgent(summary_dir=date_report_dir, data_dir=Path("output/data"))
summary_paths = await summary_agent.generate_summary(ranking_result)
```

- **StockReportAgent**: 개별 종목 마크다운 리포트 생성
  - StockAnalysisResult를 마크다운 리포트로 변환
  - 병렬 리포트 생성 (asyncio.gather)
  - 6개 카테고리별 상세 점수 및 판정 포함
  - 투자 의견 자동 생성
  - 출력: `02_stocks/{종목코드}_{종목명}.md`

- **SectorReportAgent**: 섹터 분석 마크다운 리포트 생성
  - SectorAnalysisResult를 마크다운 리포트로 변환
  - `generate_unified_report()`: 모든 섹터를 하나의 통합 리포트로 생성
  - `generate_reports()`: 섹터별 개별 리포트 생성 (기존 방식)
  - 섹터별 시가총액 가중 평균 점수
  - 상위 종목 테이블 및 강/약점 분석
  - 출력: `01_sector_report.md`

- **SummaryAgent**: 종합 리포트 및 JSON 데이터 생성
  - RankingResult를 종합 리포트로 변환
  - Top 5 추천 종목 및 선정 이유
  - 상위 섹터, 그룹별 선정 종목
  - 최종 18개 종목 테이블
  - 출력: `03_final_report.md`, `output/data/analysis_{날짜}.json`

- **WeeklySectorReportAgent**: 주간 섹터 분석 리포트 생성
  - 13개 섹터 분석 리포트 생성
  - 섹터별 주요 이슈/동향 섹션
  - 다음 주 시황 전망 템플릿
  - 주간 투자 전략 제안 섹션
  - 출력: `output/reports/weekly/YYYY-WXX_sector_report.md`

### 리포트 출력 구조

Orchestrator 실행 시 모드에 따라 다음 구조로 리포트가 생성됩니다:

```
output/reports/
├── daily/                   # 일간 리포트 폴더
│   └── YYYY-MM-DD/
│       ├── 01_sector_report.md      # 섹터 통합 분석 리포트
│       ├── 02_stocks/               # 종목별 상세 리포트
│       │   ├── 005930_삼성전자.md
│       │   ├── 000660_SK하이닉스.md
│       │   └── ...
│       └── 03_final_report.md       # 최종 종합 리포트 (Top 5, 18개 종목)
│
└── weekly/                  # 주간 리포트 폴더
    └── YYYY-WXX/
        └── sector_report.md         # 주간 섹터 분석 리포트
```

**실행 명령:**
- `uv run python main.py --daily`: 일간 리포트 생성 (기본값)
- `uv run python main.py --weekly`: 주간 섹터 리포트 생성
- `uv run python main.py --web`: API 서버 실행

## Web API

### API 서버 실행
```bash
# 기본 실행 (0.0.0.0:8000)
uv run python main.py --web

# 커스텀 포트
uv run python main.py --web --port 8080

# 커스텀 호스트/포트
uv run python main.py --web --host 127.0.0.1 --port 3000
```

서버 실행 후:
- API 문서: http://localhost:8000/docs (Swagger UI)
- ReDoc: http://localhost:8000/redoc

### API 엔드포인트

#### 헬스 체크
- `GET /api/health` - 서버 상태 확인

#### 분석 API (`/api/analysis`)
- `GET /api/analysis/latest` - 최신 분석 결과 조회
- `POST /api/analysis/run` - 분석 비동기 실행
- `GET /api/analysis/task/{task_id}` - 분석 태스크 상태 조회
- `GET /api/analysis/task/{task_id}/logs` - 분석 태스크 로그 SSE 스트리밍
- `GET /api/ranking` - Top 18, Top 5 순위 조회

#### 섹터 API (`/api/sectors`)
- `GET /api/sectors` - 전체 섹터 분석 결과 조회
- `GET /api/sectors/available` - 분석 가능한 섹터 목록
- `GET /api/sectors/{sector_name}` - 특정 섹터 상세 정보
- `GET /api/sectors/{sector_name}/stocks` - 섹터별 종목 리스트

#### 종목 API (`/api/stocks`)
- `GET /api/stocks` - 분석된 종목 리스트 (페이지네이션, 그룹 필터)
- `GET /api/stocks/{symbol}` - 특정 종목 상세 정보
- `GET /api/stocks/{symbol}/history` - 일별 주가 히스토리 (OHLCV, 최대 365일)
- `GET /api/stocks/{symbol}/supply` - 외국인/기관 순매수 추이 (최대 60일)
- `GET /api/stocks/top/{n}` - 상위 N개 종목
- `GET /api/stocks/group/{group}` - 그룹별 종목 리스트

### 사용 예시

```python
import httpx

# 최신 분석 결과 조회
response = httpx.get("http://localhost:8000/api/analysis/latest")
data = response.json()

# Top 5 종목 조회
response = httpx.get("http://localhost:8000/api/stocks/top/5")
top5 = response.json()

# 반도체 섹터 상세 조회
response = httpx.get("http://localhost:8000/api/sectors/반도체")
semiconductor = response.json()

# 분석 비동기 실행
response = httpx.post("http://localhost:8000/api/analysis/run", json={
    "mode": "daily",
    "use_cache": True
})
task_id = response.json()["task_id"]

# 태스크 상태 확인
response = httpx.get(f"http://localhost:8000/api/analysis/task/{task_id}")
status = response.json()["status"]
```

## 개발 가이드

### 패키지 관리 (uv 사용)
```bash
# 패키지 추가
uv add package-name

# 패키지 제거
uv remove package-name

# 가상환경 동기화
uv sync

# 직접 실행
uv run python script.py
```

### import 테스트
새 모듈 추가 후 반드시 import 테스트:
```bash
uv run python -c "from src.새모듈 import 클래스; print('OK')"

# web 모듈 테스트
uv run python -c "from src.web import create_app; print('Web API OK')"
```

### 코드 스타일
- 타입 힌트 사용
- docstring 작성 (Google 스타일)
- 데이터 클래스 활용 (`@dataclass`)
- 로깅 사용 (`logging` 모듈)

### 캐시 정책
| 데이터 유형 | TTL | 설명 |
|------------|-----|------|
| 주가/거래량 | 4시간 | 장중 갱신 |
| 시총 순위 | 24시간 | 일 1회 갱신 |
| 수급 데이터 | 24시간 | 일 1회 갱신 |
| 재무제표 | 7일 | 분기별 갱신 |

## 주의사항

- 이 앱은 투자 참고용이며, 실제 투자 결정은 본인의 판단에 따라야 합니다
- 네이버 금융 크롤링은 서버 정책에 따라 제한이 있을 수 있습니다
- 분석 결과는 과거 데이터 기반이므로 미래 수익을 보장하지 않습니다
