# 주식 신호 분석 앱

한국 주식의 매매 신호를 자동으로 분석하는 Python 애플리케이션입니다.

## 주요 기능

### 웹 대시보드 (추천!)
차트와 통계를 한눈에 볼 수 있는 인터랙티브 대시보드
- **메인 대시보드** (`dashboard.html`)
  - KOSPI 시장 상황 표시 (상승장/하락장/횡보장)
  - 포트폴리오 전체 요약 (총 투자금, 평가금액, 수익률)
  - 매수/매도 우선순위 종목 (시장 조정 점수 기반)
  - 종목별 상세 분석 및 가격 차트 (Chart.js)
  - 변동성 정보 표시 (ATR 기반 동적 임계값)
  - 필터링 기능 (전체/매수/매도/관망)
  - 반응형 디자인 (모바일/태블릿/PC 지원)
- **리포트 히스토리** (`history.html`) ⭐ NEW
  - 과거 분석 리포트 목록 조회
  - 리포트별 통계 요약 (종목 수, 수익률 등)
  - 특정 리포트 상세 보기
- **종목별 추이 분석** (`trends.html`) ⭐ NEW
  - 개별 종목의 매수/매도 신호 변화 추적
  - 가격, 수익률 추이 시각화
  - 시장 조정 점수 비교 차트
  - 기간별 필터링 (최근 10/20/30/60개 리포트)

### 스마트 분석 엔진
- **변동성 기반 분석** ⭐ NEW
  - ATR (Average True Range) 기반 종목별 변동성 측정
  - 동적 무릎/어깨 임계값 (변동성에 따라 자동 조정)
  - 변동성 등급 분류 (LOW/MEDIUM/HIGH)
  - 고변동성 종목: 노이즈 필터링, 저변동성 종목: 민감한 신호 감지

- **시장 필터** ⭐ NEW
  - KOSPI 지수 추세 분석 (MA20/MA60 기준)
  - 시장 국면 자동 판단 (상승장/하락장/횡보장)
  - 시장 상황에 따른 매수/매도 점수 자동 조정
  - 하락장: 매수 신호 감점, 매도 신호 가산점
  - 상승장: 매수 신호 가산점, 매도 신호 감점

- **스마트 액션 결정** ⭐ NEW
  - 임계값 + 점수 차이 기반 복합 필터링
  - 약한 신호 자동 제거 (관망으로 분류)
  - 명확한 매수/매도 신호만 추천
  - 과도한 매매 방지

- **바닥/천장 감지**: 최근 60일 기준 최저/최고가 자동 식별

- **매수 신호 분석**
  - 바닥 대비 "무릎" 위치 감지 (동적 임계값)
  - RSI 과매도 (< 30) 확인
  - 골든크로스 감지
  - 거래량 급증 확인
  - 손절가 자동 계산 (매수가 -7%)
  - 추격매수 위험도 평가

- **매도 신호 분석**
  - 천장 대비 "어깨" 위치 감지 (동적 임계값)
  - RSI 과매수 (> 70) 확인
  - 데드크로스 감지
  - 거래량 감소 확인
  - 전량/분할 매도 전략 추천

### 자동화 기능
- **자동 스케줄링**: 월~금 오전 10시, 오후 2시 자동 보고서 생성 (텍스트 + JSON)
- **리포트 히스토리 자동 저장**: 모든 분석 결과 자동 보관 및 추이 분석 지원

## 설치

이 프로젝트는 [uv](https://github.com/astral-sh/uv)를 사용합니다.

```bash
# uv 설치 (없는 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 클론
git clone <repository-url>
cd trading

# 의존성 자동 설치 (uv run 시 자동으로 설치됨)
```

## 사용 방법

### 웹 대시보드 (가장 추천!) ⭐
```bash
# 웹 대시보드 실행 - JSON 리포트 생성 + 웹서버 시작 + 브라우저 자동 열기
uv run main.py --web

# 서버 주소: http://localhost:8002/dashboard.html
# 종료: Ctrl+C
```

### 콘솔 실행
```bash
# config.py에 설정된 종목 분석
uv run main.py

# 특정 종목만 분석
uv run main.py --symbols 005930 000660 035420

# 우선순위 종목만 표시 (매수/매도 점수 상위 5개)
uv run main.py --priority

# 매수 가격을 지정하여 수익률 계산
uv run main.py --buy-prices 005930:70000 000660:120000

# 리포트를 파일로 저장
uv run main.py --save

# 옵션 조합
uv run main.py --symbols 005930 --buy-prices 005930:70000 --save
```

## 자동 스케줄링

월~금 오전 10시, 오후 2시에 자동으로 보고서를 생성할 수 있습니다.

### 스케줄러 설치
```bash
# 자동 스케줄링 설정
./scripts/setup_scheduler.sh
```

### 스케줄러 관리 (간편 도구)
```bash
# 관리 스크립트 사용 (추천!)
./scripts/manage_scheduler.sh status    # 상태 확인
./scripts/manage_scheduler.sh start     # 시작
./scripts/manage_scheduler.sh stop      # 중지
./scripts/manage_scheduler.sh restart   # 재시작
./scripts/manage_scheduler.sh test      # 수동 테스트
./scripts/manage_scheduler.sh logs      # 로그 확인
./scripts/manage_scheduler.sh reports   # 리포트 확인
./scripts/manage_scheduler.sh help      # 도움말
```

### 스케줄러 관리 (직접 명령어)
```bash
# 스케줄러 상태 확인
launchctl list | grep stock-signals

# 스케줄러 중지
launchctl unload ~/Library/LaunchAgents/com.trading.stock-signals.plist

# 스케줄러 재시작
launchctl unload ~/Library/LaunchAgents/com.trading.stock-signals.plist
launchctl load ~/Library/LaunchAgents/com.trading.stock-signals.plist

# 수동 테스트
./scripts/run_scheduled_report.sh
```

### 보고서 및 로그
- **텍스트 보고서**: `reports/` 디렉토리에 `stock_report_YYYYMMDD_HHMM.txt` 형식으로 저장
- **JSON 보고서**: `web/data/latest.json` (웹 대시보드용)
- **로그**: `logs/` 디렉토리에 저장
  - `scheduler_YYYYMMDD.log`: 스케줄러 실행 로그
  - `launchd_stdout.log`: launchd 표준 출력
  - `launchd_stderr.log`: launchd 에러 로그

### 웹 대시보드 접속
스케줄러가 실행 중이면 언제든지 웹 대시보드를 볼 수 있습니다:
```bash
# 1. 웹서버 시작 (새 터미널에서)
cd /Users/sookbunlee/work/trading/web
python3 -m http.server 8002

# 2. 브라우저에서 접속
open http://localhost:8002/dashboard.html  # 메인 대시보드
open http://localhost:8002/history.html    # 리포트 히스토리
open http://localhost:8002/trends.html     # 종목별 추이 분석
```

### REST API 엔드포인트 ⭐ NEW
웹 대시보드는 다음 API를 제공합니다:
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

## 설정

`config.py`에서 다음 항목들을 커스터마이징할 수 있습니다:

```python
# 분석할 종목 리스트
STOCK_SYMBOLS = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # NAVER
]

# 분석 기간
ANALYSIS_PERIOD_DAYS = 180  # 최근 180일

# 매수/매도 임계값 (기본값, ATR로 동적 조정됨)
BUY_KNEE_THRESHOLD = 0.15  # 바닥 대비 15%
SELL_SHOULDER_THRESHOLD = 0.15  # 천장 대비 15%
STOP_LOSS_PERCENTAGE = 0.07  # 손절가 -7%

# RSI 설정
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# 액션 결정 임계값 (신호 품질 향상) ⭐ NEW
ACTION_BUY_THRESHOLD = 30  # 매수 신호 최소 점수
ACTION_SELL_THRESHOLD = 30  # 매도 신호 최소 점수
ACTION_SCORE_DIFF_THRESHOLD = 10  # 우위 판단 최소 점수 차이
```

## 프로젝트 구조

```
stock-signals/
├── config.py                    # 설정 파일
├── main.py                      # 메인 실행 파일
├── myportfolio/                 # CSV 포트폴리오 디렉토리 (날짜별 관리)
│   ├── YYYYMMDD.csv            #   날짜별 포트폴리오 파일
│   └── example.csv             #   예제 파일
├── reports/                     # 자동 생성 텍스트 보고서
├── logs/                        # 실행 로그
├── web/                         # ⭐ 웹 대시보드
│   ├── dashboard.html          #   메인 대시보드 페이지
│   ├── history.html            #   리포트 히스토리 페이지 ⭐ NEW
│   ├── trends.html             #   종목별 추이 분석 페이지 ⭐ NEW
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css       #   스타일시트
│   │   └── js/
│   │       └── app.js          #   JavaScript (차트 & UI 로직)
│   └── data/
│       ├── latest.json         #   최신 분석 결과 (JSON)
│       └── stock_report_*.json #   과거 분석 결과 (자동 저장) ⭐ NEW
├── scripts/
│   ├── run_scheduled_report.sh  # 스케줄 실행 스크립트
│   ├── setup_scheduler.sh       # 스케줄러 설치 스크립트
│   └── manage_scheduler.sh      # 스케줄러 관리 도구
├── launchd/
│   └── com.trading.stock-signals.plist  # launchd 설정
├── src/
│   ├── data/
│   │   └── fetcher.py          # 주식 데이터 가져오기
│   ├── indicators/
│   │   ├── price_levels.py     # 바닥/천장 감지 + ATR 변동성 분석 ⭐
│   │   ├── buy_signals.py      # 매수 신호 분석 + 시장 필터 ⭐
│   │   └── sell_signals.py     # 매도 신호 분석 + 시장 필터 ⭐
│   ├── analysis/
│   │   └── analyzer.py         # 종합 분석 엔진 + 스마트 액션 결정 ⭐
│   ├── portfolio/
│   │   └── loader.py           # 포트폴리오 파일 로더 (CSV & 텍스트)
│   ├── utils/                  # 유틸리티 모듈 ⭐ NEW
│   │   └── market_analyzer.py  # KOSPI 시장 추세 분석
│   └── report/
│       ├── generator.py        # 텍스트 리포트 생성
│       ├── json_generator.py   # JSON 리포트 생성 (웹 대시보드용)
│       └── history_manager.py  # 리포트 히스토리 관리 ⭐ NEW
└── pyproject.toml
```

## 분석 로직

### 변동성 기반 동적 분석 ⭐ NEW
1. **ATR (Average True Range) 계산**: 14일 기준 종목별 변동성 측정
2. **변동성 등급 분류**:
   - LOW: ATR < 평균의 70% → 조정계수 0.8 (좁은 임계값)
   - MEDIUM: 평균의 70~130% → 조정계수 1.0 (기본값)
   - HIGH: ATR > 평균의 130% → 조정계수 1.3 (넓은 임계값)
3. **동적 임계값 적용**:
   - 무릎 임계값 = 바닥 가격 + (ATR × 2 × 조정계수)
   - 어깨 임계값 = 천장 가격 - (ATR × 2 × 조정계수)

### 시장 필터 ⭐ NEW
1. **KOSPI 추세 분석**: MA20/MA60 기준 시장 국면 판단
   - 상승장 (BULL): MA20 > MA60 (차이 2% 이상)
   - 하락장 (BEAR): MA20 < MA60 (차이 -2% 이하)
   - 횡보장 (SIDEWAYS): 차이 ±2% 이내

2. **점수 조정**:
   - 하락장: 강력 매수(80점 이상)가 아니면 50% 감점, 매도 신호 20% 가산점
   - 상승장: 매수 신호 10% 가산점, 강력 매도(80점 이상)가 아니면 30% 감점
   - 횡보장: 점수 유지

### 매수 신호
- 바닥 대비 무릎 위치 (동적 임계값, 변동성 기반)
- RSI < 30 (과매도)
- 거래량 급증 (평균의 2배 이상)
- 골든크로스 (MA20 > MA60)
- 시장 필터 적용

### 매도 신호
- 천장 대비 어깨 위치 (동적 임계값, 변동성 기반)
- RSI > 70 (과매수)
- 거래량 감소 (평균의 70% 이하)
- 데드크로스 (MA20 < MA60)
- 시장 필터 적용

### 스마트 액션 결정 ⭐ NEW
복합 조건 필터링으로 명확한 신호만 추천:
```python
if buy_score >= 30 and buy_score > sell_score + 10:
    action = 'BUY'  # 매수 신호가 충분히 강하고 우위
elif sell_score >= 30 and sell_score > buy_score + 10:
    action = 'SELL'  # 매도 신호가 충분히 강하고 우위
else:
    action = 'HOLD'  # 신호가 약하거나 애매한 경우 관망
```

## 주의사항

⚠️ **이 앱은 투자 참고용이며, 실제 투자 결정은 본인의 판단에 따라야 합니다.**

- 분석 결과는 과거 데이터 기반이므로 미래 수익을 보장하지 않습니다
- FinanceDataReader는 데이터 제공사 정책에 따라 제한이 있을 수 있습니다
- 투자에 따른 손실 책임은 투자자 본인에게 있습니다

## 라이센스

MIT License

## 기술 스택

- Python 3.12+
- FinanceDataReader: 한국 주식 데이터 수집
- pandas: 데이터 분석
- pandas-ta: 기술적 지표 계산
- uv: 패키지 관리 및 실행
- launchd: macOS 스케줄링
- Chart.js: 웹 대시보드 차트 라이브러리
- Vanilla JavaScript: 프론트엔드 (프레임워크 없음)
