# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

주식 신호 분석 앱 - FinanceDataReader를 활용하여 한국 주식의 매매 신호를 자동으로 분석하는 Python 애플리케이션입니다.

## 실행 방법

### 기본 실행
```bash
# 웹 대시보드로 보기 (가장 추천!) ⭐
uv run main.py --web

# 콘솔에서 분석 결과 확인 (myportfolio 디렉토리의 최신 CSV 파일 자동 사용)
uv run main.py

# 특정 날짜의 CSV 파일 지정
uv run main.py --portfolio myportfolio/20251015.csv

# 특정 종목만 분석
uv run main.py --symbols 005930 000660 035420

# 우선순위 종목만 표시
uv run main.py --priority

# 리포트를 파일로 저장
uv run main.py --save

# 매수 가격을 지정하여 수익률 계산 (CSV 파일의 매수가보다 우선)
uv run main.py --buy-prices 005930:70000 000660:120000
```

### 웹 대시보드 사용 (추천!)
```bash
# 웹 대시보드 실행 - JSON 리포트 생성 + 웹서버 시작 + 브라우저 자동 열기
uv run main.py --web

# 서버 주소: http://localhost:8002/dashboard.html
# 종료: Ctrl+C
```

**웹 대시보드 기능:**
- **⭐ NEW: KOSPI 시장 상황 표시** (상승장/하락장/횡보장, MA20-MA60 추세 차이)
- 포트폴리오 전체 요약 (총 투자금, 평가금액, 수익률)
- 매수/매도 우선순위 종목 한눈에 보기 (시장 조정 점수 기반)
- 종목별 상세 분석 및 가격 차트 (Chart.js)
- **⭐ NEW: 변동성 정보 표시 (ATR 기반 동적 임계값)**
- 필터링 기능 (전체/매수/매도/관망)
- 반응형 디자인 (모바일/태블릿/PC 지원)
- 실시간 새로고침 버튼
- **⭐ NEW: 리포트 히스토리** - 과거 리포트 조회 및 비교
- **⭐ NEW: 종목별 추이 분석** - 매수/매도 점수 및 가격 변화 시각화

### 포트폴리오 CSV 파일 사용 (추천!)
`myportfolio/` 디렉토리에 날짜별 CSV 파일로 포트폴리오를 관리합니다:

```bash
# myportfolio 디렉토리 구조
myportfolio/
├── 20251015.csv  # 오늘 날짜
├── 20251014.csv  # 어제 날짜
└── example.csv   # 예제 파일
```

CSV 파일 형식 (엑셀에서도 편집 가능):
```csv
종목코드,매수가격,수량,종목명
005930,71000,150,삼성전자
000660,120000,30,SK하이닉스
035420,195000,40,NAVER
035720,60000,50,카카오
```

**장점:**
- 날짜별 포트폴리오 히스토리 관리
- 엑셀/Google Sheets에서 편집 가능
- 수량 정보도 함께 관리 (향후 기능 확장 가능)
- 자동으로 최신 날짜 파일을 찾아서 사용

### 포트폴리오 우선순위
프로그램은 다음 순서로 포트폴리오를 찾습니다:

1. `--portfolio` 옵션으로 지정한 파일 (CSV 또는 텍스트)
2. `myportfolio/` 디렉토리의 최신 CSV 파일 ⭐ **추천**
3. `.portfolio` 파일 (텍스트 형식)
4. `--symbols` 옵션으로 지정한 종목들
5. `config.py`의 `STOCK_SYMBOLS` 리스트

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
├── myportfolio/                 # ⭐ CSV 포트폴리오 디렉토리 (날짜별 관리)
│   ├── 20251015.csv            #    오늘 날짜 포트폴리오
│   ├── 20251014.csv            #    어제 날짜 포트폴리오
│   └── example.csv             #    예제 파일
├── .portfolio                   # 텍스트 포트폴리오 (옵션)
├── .portfolio.example           # 포트폴리오 파일 예제
├── reports/                     # 생성된 텍스트 리포트 저장 디렉토리
├── web/                         # ⭐ 웹 대시보드
│   ├── dashboard.html          #    메인 대시보드 페이지
│   ├── history.html            #    ⭐ NEW: 리포트 히스토리 페이지
│   ├── trends.html             #    ⭐ NEW: 종목별 추이 분석 페이지
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css       #    스타일시트
│   │   └── js/
│   │       └── app.js          #    JavaScript (차트 & UI 로직)
│   └── data/                   #    JSON 리포트 저장 위치
│       ├── latest.json         #    최신 분석 결과
│       └── stock_report_*.json #    과거 분석 결과 (자동 저장)
├── src/
│   ├── data/
│   │   └── fetcher.py          # 주식 데이터 가져오기 (FinanceDataReader)
│   ├── indicators/
│   │   ├── price_levels.py     # 바닥/천장 감지
│   │   ├── buy_signals.py      # 매수 신호 분석 (RSI, 골든크로스 등)
│   │   └── sell_signals.py     # 매도 신호 분석 (데드크로스 등)
│   ├── analysis/
│   │   └── analyzer.py         # 종합 분석 엔진
│   ├── portfolio/
│   │   └── loader.py           # 포트폴리오 파일 로더 (CSV & 텍스트)
│   ├── utils/                  # ⭐ NEW: 유틸리티 모듈
│   │   ├── __init__.py
│   │   └── market_analyzer.py  # 시장 추세 분석 (KOSPI)
│   └── report/
│       ├── generator.py        # 텍스트 리포트 생성기
│       ├── json_generator.py   # JSON 리포트 생성기 (웹 대시보드용)
│       └── history_manager.py  # ⭐ NEW: 리포트 히스토리 관리
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
   - **⭐ NEW: ATR (Average True Range) 계산 및 변동성 분석**
   - **⭐ NEW: 동적 무릎/어깨 임계값 (ATR 기반, 종목별 맞춤형)**
   - 변동성 등급 분류 (LOW/MEDIUM/HIGH)

3. **MarketAnalyzer** (src/utils/market_analyzer.py) ⭐ NEW
   - KOSPI 지수 데이터 가져오기 및 캐싱
   - MA20/MA60 기반 시장 추세 분석 (BULL/BEAR/SIDEWAYS)
   - 시장 변동성 계산
   - 싱글톤 패턴으로 효율적 데이터 관리

4. **BuySignalAnalyzer** (src/indicators/buy_signals.py)
   - 매수 신호 분석: RSI 과매도, 거래량 급증, 골든크로스
   - **⭐ NEW: 시장 필터 적용** (하락장 50% 감점, 상승장 10% 가산점)
   - 손절가 계산 (매수가 -7%)
   - 추격매수 위험도 평가
   - 매수 점수 (0-100) 산출 및 시장 조정 점수

5. **SellSignalAnalyzer** (src/indicators/sell_signals.py)
   - 매도 신호 분석: RSI 과매수, 거래량 감소, 데드크로스
   - **⭐ NEW: 시장 필터 적용** (상승장 30% 감점, 하락장 20% 가산점)
   - 변동성 계산 및 전량/분할 매도 전략 추천
   - 수익률 기반 매도 판단
   - 매도 점수 (0-100) 산출 및 시장 조정 점수

6. **StockAnalyzer** (src/analysis/analyzer.py)
   - 위 모든 분석기를 통합
   - **⭐ NEW: MarketAnalyzer 통합** (모든 종목 분석 시 시장 추세 전달)
   - 여러 종목 동시 분석 지원
   - 시장 조정 점수 기반 매수/매도 우선순위 종목 추출

7. **ReportGenerator** (src/report/generator.py)
   - 분석 결과를 텍스트 형태로 출력
   - 텍스트 파일 저장 기능

8. **JsonReportGenerator** (src/report/json_generator.py)
   - 분석 결과를 JSON 형식으로 변환
   - **⭐ NEW: 시장 정보 및 조정 점수 포함**
   - 포트폴리오 요약 계산 (투자금, 평가금액, 수익률)
   - 웹 대시보드용 데이터 생성

9. **ReportHistoryManager** (src/report/history_manager.py) ⭐ NEW
   - 저장된 모든 JSON 리포트 관리
   - 리포트 목록 조회 및 필터링
   - 종목별 추이 데이터 추출 (매수/매도 점수, 가격 변화)
   - REST API 엔드포인트로 데이터 제공

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
1. **바닥 대비 무릎 도달**:
   - **⭐ NEW: 동적 임계값 사용** - 바닥 가격 + (ATR × 2 × 조정계수)
   - 고변동성 종목은 넓은 임계값, 저변동성 종목은 좁은 임계값 적용
2. **RSI 과매도**: RSI < 30
3. **거래량 급증**: 평균 거래량의 2배 이상
4. **골든크로스**: MA20이 MA60을 상향 돌파
5. **추격매수 체크**: 바닥 대비 25% 이상 상승 시 경고
6. **⭐ NEW: 시장 필터**:
   - 하락장: 강력 매수(80점 이상)가 아니면 50% 감점
   - 상승장: 모든 매수 신호에 10% 가산점
   - 횡보장: 점수 유지

### 매도 신호
1. **천장 대비 어깨 도달**:
   - **⭐ NEW: 동적 임계값 사용** - 천장 가격 - (ATR × 2 × 조정계수)
   - 변동성에 따라 자동으로 임계값 조정
2. **RSI 과매수**: RSI > 70
3. **거래량 감소**: 평균 거래량의 70% 이하
4. **데드크로스**: MA20이 MA60을 하향 돌파
5. **매도 전략**: 수익률과 변동성에 따라 전량/분할 매도 추천
6. **⭐ NEW: 시장 필터**:
   - 상승장: 강력 매도(80점 이상)가 아니면 30% 감점 (보유 유리)
   - 하락장: 모든 매도 신호에 20% 가산점
   - 횡보장: 점수 유지

### ⭐ 변동성 기반 분석 (Phase 1 신규 기능)

**ATR (Average True Range) 활용:**
- 14일 기준 ATR 계산으로 종목별 가격 변동폭 측정
- 변동성 등급 자동 분류:
  - **LOW**: ATR < 평균의 70% → 조정계수 0.8 (좁은 임계값)
  - **MEDIUM**: 평균의 70~130% → 조정계수 1.0 (기본값)
  - **HIGH**: ATR > 평균의 130% → 조정계수 1.3 (넓은 임계값)

**동적 임계값의 장점:**
- 삼성전자 같은 안정적 종목: 작은 움직임도 신호로 감지
- 바이오/테마주 같은 고변동성 종목: 노이즈 필터링
- 시장 상황 변화에 자동으로 적응

### ⭐ 시장 필터 (Phase 1 신규 기능)

**KOSPI 지수 추세 분석:**
- MA20/MA60 기준으로 시장 국면 자동 판단
- 추세 구분:
  - **상승장 (BULL)**: MA20 > MA60 (차이 2% 이상)
  - **하락장 (BEAR)**: MA20 < MA60 (차이 -2% 이하)
  - **횡보장 (SIDEWAYS)**: 차이 ±2% 이내

**시장 필터 적용 효과:**
- 하락장에서 무분별한 매수 방지
- 상승장에서 매수 기회 적극 활용
- 상승장에서 성급한 매도 방지
- 하락장에서 빠른 손절 유도

## ⭐ 리포트 히스토리 및 추이 분석 (Phase 2 신규 기능)

### 리포트 히스토리
웹 대시보드에서 과거 분석 리포트를 조회하고 비교할 수 있습니다.

**접근 방법:**
- 웹 대시보드 네비게이션에서 "히스토리" 클릭
- 또는 직접 접속: http://localhost:8002/history.html

**주요 기능:**
- 📋 전체 리포트 목록 테이블
  - 생성 날짜/시간
  - 분석 종목 수
  - 매수가 정보가 있는 종목 수
  - 포트폴리오 수익률
  - 총 수익금액
- 📊 통계 요약 (전체 리포트 수, 최신 리포트 정보)
- 🔍 특정 리포트 선택 → 대시보드에서 상세 보기
- ⚡ 실시간 새로고침

### 종목별 추이 분석
개별 종목의 매수/매도 신호 변화와 가격 추이를 시각화합니다.

**접근 방법:**
- 웹 대시보드 네비게이션에서 "추이 분석" 클릭
- 또는 직접 접속: http://localhost:8002/trends.html

**주요 기능:**
1. **종목 선택**
   - 드롭다운에서 분석할 종목 선택
   - 자동으로 모든 종목 목록 로드

2. **기간 선택**
   - 최근 10/20/30/60개 리포트 선택 가능
   - 충분한 데이터로 추세 파악

3. **4가지 차트 제공**
   - 📈 **가격 추이 차트**: 시간에 따른 주가 변화
   - 🎯 **매수/매도 점수 차트**: 원본 신호 점수 비교
   - 🔄 **시장 조정 점수 차트**: 시장 상황 반영 후 점수
   - 💰 **수익률 차트**: 매수가 기준 수익률 변화 (있는 경우)

4. **종목 정보 요약**
   - 현재가
   - 최근 매수/매도 점수
   - 최근 액션 (BUY/SELL/HOLD)
   - 수익률

**활용 방법:**
- 매수 타이밍 검증: 과거 신호가 실제로 좋은 타이밍이었는지 확인
- 매도 타이밍 분석: 어떤 신호에서 매도했을 때 최적이었는지 학습
- 시장 필터 효과: 조정 전후 점수 비교로 시장 상황의 영향도 파악
- 포트폴리오 최적화: 신호의 정확도를 바탕으로 종목 비중 조정

### REST API 엔드포인트

히스토리 기능은 다음 API를 통해 접근할 수 있습니다:

```bash
# 전체 리포트 목록
GET /api/reports

# 특정 리포트 조회
GET /api/report?filename=stock_report_20251017_094443.json

# 종목별 추이 데이터
GET /api/trends?symbol=005930&limit=30

# 전체 종목 목록
GET /api/symbols
```

**응답 예시:**
```json
// /api/trends?symbol=005930&limit=5
{
  "symbol": "005930",
  "name": "삼성전자",
  "data": [
    {
      "date": "2025-10-16T15:39:24.896734",
      "price": 97700,
      "buy_score": 0,
      "sell_score": 25,
      "buy_adjusted_score": 0,
      "sell_adjusted_score": 25,
      "action": "SELL",
      "profit_rate": 0.072,
      "market_trend": "BULL"
    }
    // ... more data
  ]
}
```

## 개발 가이드

### 새로운 기술적 지표 추가
1. `pandas-ta` 라이브러리 활용
2. `buy_signals.py` 또는 `sell_signals.py`에 계산 메서드 추가
3. `analyze_buy_signals()` 또는 `analyze_sell_signals()`에 로직 통합

### 새로운 종목 추가

**방법 1: CSV 파일 편집 (가장 추천!)**
`myportfolio/YYYYMMDD.csv` 파일을 엑셀이나 텍스트 에디터로 편집:
```csv
종목코드,매수가격,수량,종목명
005930,71000,150,삼성전자
000660,120000,30,SK하이닉스
035720,60000,50,카카오
```

**방법 2: .portfolio 파일 사용**
`.portfolio` 파일에 종목 추가:
```
005930:71000  # 삼성전자
000660:120000 # SK하이닉스
035720        # 카카오 (새로 추가)
```

**방법 3: config.py 수정**
`config.py`의 `STOCK_SYMBOLS` 리스트에 종목 코드 추가:
```python
STOCK_SYMBOLS = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035720",  # 카카오 (새로 추가)
]
```

### 매수/매도 임계값 조정
`config.py`에서 각종 임계값 조정 가능:
- 무릎/어깨 위치, 손절가, RSI 기준 등

## 주의사항

- 이 앱은 투자 참고용이며, 실제 투자 결정은 본인의 판단에 따라야 합니다
- FinanceDataReader는 데이터 제공사 정책에 따라 제한이 있을 수 있습니다
- 분석 결과는 과거 데이터 기반이므로 미래 수익을 보장하지 않습니다
