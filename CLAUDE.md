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
# 전체 분석 실행
uv run python main.py

# 섹터 분석만
uv run python main.py --sector-only

# 캐시 없이 상세 로그
uv run python main.py --no-cache -v

# 도움말
uv run python main.py --help
```

## 프로젝트 구조

```
trading/
├── CLAUDE.md                    # 이 파일
├── README.md                    # 프로젝트 소개
├── pyproject.toml               # 의존성 정의
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                    # 핵심 설정 및 엔진
│   │   ├── __init__.py
│   │   ├── config.py            # SECTORS(11개), RUBRIC_WEIGHTS(V2), INVESTMENT_GRADES
│   │   ├── rubric.py            # RubricEngine V2 (6개 카테고리)
│   │   ├── orchestrator.py      # Orchestrator - 전체 파이프라인 조율
│   │   └── logging_config.py    # 로깅 설정
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
│   │   │   └── news_agent.py           # 뉴스/센티먼트 수집
│   │   │
│   │   ├── analysis/            # 분석 에이전트
│   │   │   ├── __init__.py
│   │   │   ├── stock_analyzer.py       # 개별 종목 루브릭 점수
│   │   │   ├── sector_analyzer.py      # 섹터 시가총액 가중 평균
│   │   │   └── ranking_agent.py        # 4개 그룹 순위, 최종 18개, Top 3
│   │   │
│   │   └── report/              # 리포트 에이전트
│   │       ├── __init__.py
│   │       ├── stock_report_agent.py   # 개별 종목 마크다운 리포트
│   │       ├── sector_report_agent.py  # 섹터 분석 마크다운 리포트
│   │       └── summary_agent.py        # 종합 리포트 및 JSON 데이터
│   │
│   └── output/                  # 출력 디렉토리
│       ├── data/
│       │   └── cache/           # 캐시 파일 저장
│       └── reports/
│           ├── sectors/         # 섹터별 리포트
│           ├── stocks/          # 종목별 리포트
│           └── summary/         # 요약 리포트
│
├── tests/                       # 테스트 (279개)
│   ├── core/                    # rubric V1, V2 테스트 (166개)
│   ├── agents/
│   │   ├── data/                # 데이터 에이전트 테스트 (64개)
│   │   └── analysis/            # 분석 에이전트 테스트 (49개)
│
└── docs/
    └── architecture.md          # 아키텍처 설명
```

## 핵심 모듈 설명

### src/core/config.py
프로젝트 전역 설정을 정의합니다.

```python
# 분석 대상 섹터 및 대표 종목 (11개 섹터)
SECTORS = {
    "반도체": ["005930", "000660", "042700", "403870", "058470"],
    "조선": ["010140", "009540", "042660", "003620", "010620"],
    "방산": ["012450", "047810", "064350", "079550", "273640"],
    "원전": ["034020", "009830", "071970", "267260", "004490"],
    "전력기기": ["267260", "032560", "298040", "042670", "009450"],
    "바이오": ["207940", "068270", "326030", "141080", "145020"],
    "로봇": ["336260", "108490", "090710", "309930", "950140"],
    "자동차": ["005380", "000270", "012330", "204320", "161390"],
    "신재생에너지": ["009830", "112610", "117580", "093370", "281740"],
    "지주": ["000810", "003550", "001040", "005490", "006400"],
    "뷰티": ["090430", "285130", "263750", "078930", "051900"],
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
FinanceDataReader를 사용한 주식 데이터 수집.

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
print(result.final_top3) # Top 3 종목
```

- **StockAnalyzer**: 개별 종목 루브릭 점수 산출
  - 4개 그룹별 분석: KOSPI Top10, KOSPI 11~20, KOSDAQ Top10, 섹터별
  - RubricEngine V2 기반 점수 계산

- **SectorAnalyzer**: 섹터별 점수 산출
  - 시가총액 가중 평균 점수 계산
  - 상위 섹터 선정

- **RankingAgent**: 최종 순위 산정
  - 4개 그룹에서 각 3개 종목 선정 (KOSPI 9개 + KOSDAQ 3개 + 섹터 9개)
  - 중복 제거 후 최종 18개 종목 집계
  - Top 3 선정 (가중치: 총점 70%, 수급 15%, 성장성 15%)

### src/agents/report/
리포트 생성 에이전트 모듈.

```python
from src.agents.report import StockReportAgent, SectorReportAgent, SummaryAgent

# 개별 종목 리포트 생성
stock_report_agent = StockReportAgent()
report_paths = await stock_report_agent.generate_reports(stock_results)
# output/reports/stocks/ 에 마크다운 리포트 저장

# 섹터 리포트 생성
sector_report_agent = SectorReportAgent()
sector_paths = await sector_report_agent.generate_reports(sector_results)
# output/reports/sectors/ 에 마크다운 리포트 저장

# 종합 리포트 생성
summary_agent = SummaryAgent()
summary_paths = await summary_agent.generate_summary(ranking_result)
# output/reports/summary/ 에 종합 리포트 저장
# output/data/ 에 JSON 데이터 저장
```

- **StockReportAgent**: 개별 종목 마크다운 리포트 생성
  - StockAnalysisResult를 마크다운 리포트로 변환
  - 병렬 리포트 생성 (asyncio.gather)
  - 6개 카테고리별 상세 점수 및 판정 포함
  - 투자 의견 자동 생성

- **SectorReportAgent**: 섹터 분석 마크다운 리포트 생성
  - SectorAnalysisResult를 마크다운 리포트로 변환
  - 섹터별 시가총액 가중 평균 점수
  - 상위 종목 테이블 및 강/약점 분석
  - 섹터 전망 자동 생성

- **SummaryAgent**: 종합 리포트 및 JSON 데이터 생성
  - RankingResult를 종합 리포트로 변환
  - Top 3 추천 종목 및 선정 이유
  - 상위 섹터, 그룹별 선정 종목
  - 최종 18개 종목 테이블
  - JSON 데이터 저장 (API 연동용)

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
- FinanceDataReader는 데이터 제공사 정책에 따라 제한이 있을 수 있습니다
- 분석 결과는 과거 데이터 기반이므로 미래 수익을 보장하지 않습니다
