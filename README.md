# Stock Signal Analyzer

**섹터 순환 투자 전략 분석 시스템**

한국 주식 시장의 섹터별 투자 기회를 분석하고, 루브릭 기반 점수로 투자 등급을 산출하는 Python 애플리케이션입니다.

## 현재 상태

| 단계 | 상태 | 설명 |
|------|------|------|
| Phase 0 | 완료 | 기본 인프라 (config, fetcher, cache, rubric, agents) |
| Phase 1 | 진행 중 | Orchestrator 및 전체 파이프라인 연결 |

## 기술 스택

- **Python 3.12+**
- **FinanceDataReader**: 한국 주식 데이터 수집
- **pandas / pandas-ta**: 데이터 분석 및 기술적 지표
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

## 핵심 기능

### 섹터 기반 분석
- 반도체, 조선 등 섹터별 대표 종목 분석
- 섹터 확장 용이 (config.py에서 관리)

### 루브릭 평가 시스템
- 기술적 분석 (30점): 추세, RSI, 지지/저항
- 수급 분석 (25점): 외국인, 기관, 거래대금
- 펀더멘털 분석 (25점): PER, 성장률, 부채비율
- 시장 환경 (20점): 뉴스, 섹터모멘텀, 애널리스트

### 투자 등급 산출
| 등급 | 점수 범위 |
|------|----------|
| Strong Buy | 80-100 |
| Buy | 60-79 |
| Hold | 40-59 |
| Sell | 20-39 |
| Strong Sell | 0-19 |

### 에이전트 기반 데이터 수집
- MarketDataAgent: 시장 데이터 (주가, 거래량, 지표)
- FundamentalAgent: 재무제표 (PER, PBR, 성장률)
- NewsAgent: 뉴스 센티먼트

## 프로젝트 구조

```
trading/
├── src/
│   ├── core/           # 설정 및 평가 엔진
│   │   ├── config.py   # SECTORS, RUBRIC_WEIGHTS, INVESTMENT_GRADES
│   │   └── rubric.py   # RubricEngine
│   ├── data/           # 데이터 수집 및 캐싱
│   │   ├── fetcher.py  # StockDataFetcher
│   │   └── cache.py    # CacheManager
│   └── agents/         # 에이전트 기반 수집
│       ├── base_agent.py
│       └── data/       # MarketDataAgent, FundamentalAgent, NewsAgent
├── docs/
│   └── architecture.md # 아키텍처 문서
├── CLAUDE.md           # Claude Code 가이드
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
