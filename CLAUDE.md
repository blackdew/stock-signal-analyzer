# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

주식 신호 분석 앱 - FinanceDataReader를 활용하여 한국 주식의 매매 신호를 자동으로 분석하는 Python 애플리케이션입니다.

## 실행 방법

### 기본 실행
```bash
# config.py에 설정된 종목 분석
uv run main.py

# 특정 종목만 분석
uv run main.py --symbols 005930 000660 035420

# 우선순위 종목만 표시
uv run main.py --priority

# 리포트를 파일로 저장
uv run main.py --save

# 매수 가격을 지정하여 수익률 계산
uv run main.py --buy-prices 005930:70000 000660:120000
```

### 의존성 관리
```bash
# 패키지 추가
uv add package-name

# 패키지 제거
uv remove package-name

# 가상환경 활성화
source .venv/bin/activate

# 가상환경 비활성화
deactivate
```

## 프로젝트 구조

```
stock-signals/
├── config.py                    # 설정 파일 (종목, 임계값 등)
├── main.py                      # 메인 실행 파일
├── src/
│   ├── data/
│   │   └── fetcher.py          # 주식 데이터 가져오기 (FinanceDataReader)
│   ├── indicators/
│   │   ├── price_levels.py     # 바닥/천장 감지
│   │   ├── buy_signals.py      # 매수 신호 분석 (RSI, 골든크로스 등)
│   │   └── sell_signals.py     # 매도 신호 분석 (데드크로스 등)
│   ├── analysis/
│   │   └── analyzer.py         # 종합 분석 엔진
│   └── report/
│       └── generator.py        # 리포트 생성기
└── pyproject.toml              # 프로젝트 의존성
```

## 핵심 아키텍처

### 데이터 흐름
1. **StockDataFetcher** (src/data/fetcher.py)
   - FinanceDataReader로 주가 데이터 가져오기
   - 기본 기술적 지표 계산 (MA20, MA60, 거래량 평균)

2. **PriceLevelDetector** (src/indicators/price_levels.py)
   - 최근 N일 기준 바닥(최저가)/천장(최고가) 감지
   - 현재가가 바닥/천장 대비 어느 위치인지 계산
   - "무릎"(바닥 +15%), "어깨"(천장 -15%) 위치 판단

3. **BuySignalAnalyzer** (src/indicators/buy_signals.py)
   - 매수 신호 분석: RSI 과매도, 거래량 급증, 골든크로스
   - 손절가 계산 (매수가 -7%)
   - 추격매수 위험도 평가
   - 매수 점수 (0-100) 산출

4. **SellSignalAnalyzer** (src/indicators/sell_signals.py)
   - 매도 신호 분석: RSI 과매수, 거래량 감소, 데드크로스
   - 변동성 계산 및 전량/분할 매도 전략 추천
   - 수익률 기반 매도 판단
   - 매도 점수 (0-100) 산출

5. **StockAnalyzer** (src/analysis/analyzer.py)
   - 위 모든 분석기를 통합
   - 여러 종목 동시 분석 지원
   - 매수/매도 우선순위 종목 추출

6. **ReportGenerator** (src/report/generator.py)
   - 분석 결과를 보기 좋은 형태로 출력
   - 파일 저장 기능

## 설정 (config.py)

주요 설정 항목:
- `STOCK_SYMBOLS`: 분석할 종목 코드 리스트
- `ANALYSIS_PERIOD_DAYS`: 분석 기간 (기본 180일)
- `BUY_KNEE_THRESHOLD`: 무릎 판단 기준 (기본 15%)
- `SELL_SHOULDER_THRESHOLD`: 어깨 판단 기준 (기본 15%)
- `STOP_LOSS_PERCENTAGE`: 손절가 비율 (기본 7%)
- `RSI_OVERSOLD/OVERBOUGHT`: RSI 과매도/과매수 기준

## 분석 로직

### 매수 신호
1. **바닥 대비 무릎 도달**: 바닥 가격 대비 15% 상승 시
2. **RSI 과매도**: RSI < 30
3. **거래량 급증**: 평균 거래량의 2배 이상
4. **골든크로스**: MA20이 MA60을 상향 돌파
5. **추격매수 체크**: 바닥 대비 25% 이상 상승 시 경고

### 매도 신호
1. **천장 대비 어깨 도달**: 천장 가격 대비 15% 하락 시
2. **RSI 과매수**: RSI > 70
3. **거래량 감소**: 평균 거래량의 70% 이하
4. **데드크로스**: MA20이 MA60을 하향 돌파
5. **매도 전략**: 수익률과 변동성에 따라 전량/분할 매도 추천

## 개발 가이드

### 새로운 기술적 지표 추가
1. `pandas-ta` 라이브러리 활용
2. `buy_signals.py` 또는 `sell_signals.py`에 계산 메서드 추가
3. `analyze_buy_signals()` 또는 `analyze_sell_signals()`에 로직 통합

### 새로운 종목 추가
`config.py`의 `STOCK_SYMBOLS` 리스트에 종목 코드 추가:
```python
STOCK_SYMBOLS = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    # 여기에 추가
]
```

### 매수/매도 임계값 조정
`config.py`에서 각종 임계값 조정 가능:
- 무릎/어깨 위치, 손절가, RSI 기준 등

## 주의사항

- 이 앱은 투자 참고용이며, 실제 투자 결정은 본인의 판단에 따라야 합니다
- FinanceDataReader는 데이터 제공사 정책에 따라 제한이 있을 수 있습니다
- 분석 결과는 과거 데이터 기반이므로 미래 수익을 보장하지 않습니다
