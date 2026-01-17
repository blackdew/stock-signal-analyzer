# CLAUDE.md

이 파일은 Claude Code가 이 저장소의 코드를 다룰 때 참고하는 가이드입니다.

## 프로젝트 개요

**섹터 순환 투자 전략 분석 시스템** - 한국 주식 시장의 섹터별 투자 기회를 분석하고 루브릭 기반 점수로 투자 등급을 산출하는 Python 애플리케이션입니다.

### 현재 상태
- **Phase 0 완료**: 기본 인프라 구축 (config, fetcher, cache, rubric, agents)
- **개발 진행 중**: Orchestrator, 전체 파이프라인 연결

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

# agents 테스트
uv run python -c "from src.agents.data import MarketDataAgent; print('MarketDataAgent OK')"
```

### 메인 실행 (개발 중)
```bash
# 현재 main.py는 기존 주식 신호 분석용 (향후 재작성 예정)
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
│   │   ├── config.py            # SECTORS, RUBRIC_WEIGHTS, INVESTMENT_GRADES
│   │   ├── rubric.py            # RubricEngine (루브릭 평가 엔진)
│   │   └── orchestrator.py      # (개발 중) 전체 파이프라인 조율
│   │
│   ├── data/                    # 데이터 수집 및 캐싱
│   │   ├── __init__.py
│   │   ├── fetcher.py           # StockDataFetcher, StockInfo, StockData
│   │   └── cache.py             # CacheManager, CacheTTL
│   │
│   ├── agents/                  # 에이전트 기반 데이터 수집
│   │   ├── __init__.py
│   │   ├── base_agent.py        # BaseAgent (추상 클래스)
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── market_data_agent.py    # 시장 데이터 수집
│   │   │   ├── fundamental_agent.py    # 재무제표 수집
│   │   │   └── news_agent.py           # 뉴스/센티먼트 수집
│   │   ├── analysis/
│   │   │   └── __init__.py      # (개발 중)
│   │   └── report/
│   │       └── __init__.py      # (개발 중)
│   │
│   └── output/                  # 출력 디렉토리
│       ├── data/
│       │   └── cache/           # 캐시 파일 저장
│       └── reports/
│           ├── sectors/         # 섹터별 리포트
│           ├── stocks/          # 종목별 리포트
│           └── summary/         # 요약 리포트
│
└── docs/
    └── architecture.md          # 아키텍처 설명
```

## 핵심 모듈 설명

### src/core/config.py
프로젝트 전역 설정을 정의합니다.

```python
# 분석 대상 섹터 및 대표 종목
SECTORS = {
    "반도체": ["005930", "000660", "042700"],  # 삼성전자, SK하이닉스, 한미반도체
    "조선": ["010140", "009540", "042660"],    # 삼성중공업, 한국조선해양, 대우조선해양
}

# 루브릭 가중치
RUBRIC_WEIGHTS = {
    "technical": 30,    # 기술적 분석
    "supply": 25,       # 수급 분석
    "fundamental": 25,  # 펀더멘털 분석
    "market": 20,       # 시장 환경
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
루브릭 기반 투자 점수 산출 엔진.

```python
from src.core.rubric import RubricEngine, RubricResult

engine = RubricEngine()

result = engine.calculate(
    symbol="005930",
    name="삼성전자",
    market_data=market_data,
    fundamental_data=fundamental_data,
    news_data=news_data,
    low_52w=50000,
    high_52w=80000
)

print(f"총점: {result.total_score}, 등급: {result.grade}")
# 출력: 총점: 65.3, 등급: Buy
```

**평가 카테고리 (100점 만점):**
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
- **FundamentalAgent**: 재무제표 수집 (PER, PBR, 성장률, 부채비율)
- **NewsAgent**: 뉴스 및 센티먼트 분석

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
