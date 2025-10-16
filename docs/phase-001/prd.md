# Phase 1 개선사항 PRD (Product Requirements Document)

## 📋 개요

**버전**: 1.0
**작성일**: 2025-10-16
**목표 완료일**: 2주 이내
**담당**: 개발팀

### 목적
현재 매매 신호 분석 시스템의 치명적인 문제점들을 신속하게 개선하여, 실전 투자 환경에서 안정적으로 사용할 수 있는 기반을 마련한다.

### 배경
전문가 패널 분석 결과, 현재 시스템은 다음과 같은 치명적 문제를 가지고 있음:
- 정적 임계값으로 인한 종목별 특성 무시
- 시장 전체 상황을 고려하지 않는 매매 신호
- 손절 로직의 불완전한 구현
- 부실한 예외 처리 및 에러 핸들링

---

## 🎯 Phase 1 개선 목표

### 핵심 목표
1. **변동성 기반 동적 임계값 도입** - 종목별 특성 반영
2. **시장 필터 추가** - 전체 시장 상황 고려
3. **손절 로직 강화** - 리스크 관리 개선
4. **예외 처리 및 로깅 개선** - 안정성 향상

### 성공 지표
- [x] **모든 임계값이 변동성 기반으로 동적 조정됨** ✅ (2025-10-16 완료)
  - ATR 계산 및 변동성 등급 분류 구현
  - 동적 무릎/어깨 임계값 적용
- [ ] KOSPI 추세에 따라 매수/매도 점수가 조정됨 (다음 단계)
- [ ] 손실 중인 종목에 대한 명확한 손절 신호 제공 (다음 단계)
- [ ] 모든 API 호출 및 계산에 예외 처리 적용 (일부 완료, ATR 예외 처리)
- [ ] 주요 이벤트에 대한 로깅 완료 (계획 단계)

---

## 📝 요구사항 상세

### 1. 변동성 기반 동적 임계값

#### 1.1 ATR (Average True Range) 계산
**Priority**: P0 (최우선)

**요구사항**:
- 각 종목별로 14일 기준 ATR 계산
- ATR을 활용한 동적 무릎/어깨 임계값 설정
- 변동성이 높은 종목은 더 넓은 임계값 적용

**기술 사양**:
```python
# ATR 계산
atr_period = 14
atr = ta.atr(high=df['High'], low=df['Low'], close=df['Close'], length=atr_period)

# 동적 무릎 임계값 계산
floor_price = get_floor_price(df)
dynamic_knee_threshold = floor_price + (atr * 2)  # ATR의 2배

# 동적 어깨 임계값 계산
ceiling_price = get_ceiling_price(df)
dynamic_shoulder_threshold = ceiling_price - (atr * 2)
```

**검증 방법**:
- 삼성전자(저변동성)와 바이오 종목(고변동성)에 대해 임계값 비교
- ATR 2배가 적절한지 1.5배, 2.5배와 비교 테스트

#### 1.2 표준편차 기반 보조 지표
**Priority**: P1

**요구사항**:
- 20일 기준 가격 변동성(표준편차) 계산
- ATR과 함께 사용하여 임계값 정확도 향상
- 변동성 등급 분류 (낮음/중간/높음)

**기술 사양**:
```python
# 표준편차 계산
std_period = 20
price_std = df['Close'].rolling(window=std_period).std()
current_std = price_std.iloc[-1]

# 변동성 등급
volatility_level = 'LOW' if current_std < threshold_low else \
                  'HIGH' if current_std > threshold_high else 'MEDIUM'

# 등급별 임계값 조정 계수
adjustment_factor = {
    'LOW': 0.8,    # 낮은 변동성: 좁은 임계값
    'MEDIUM': 1.0,  # 중간 변동성: 기본값
    'HIGH': 1.3     # 높은 변동성: 넓은 임계값
}
```

---

### 2. 시장 필터 추가

#### 2.1 KOSPI 추세 분석
**Priority**: P0 (최우선)

**요구사항**:
- KOSPI 지수의 최근 추세 분석 (상승/하락/횡보)
- MA20/MA60 기준으로 시장 국면 판단
- 하락장에서는 매수 신호에 페널티 적용

**기술 사양**:
```python
def analyze_market_trend(market_index='KS11'):
    """
    KOSPI 추세 분석

    Returns:
        'BULL': 상승장 (MA20 > MA60)
        'BEAR': 하락장 (MA20 < MA60)
        'SIDEWAYS': 횡보장 (MA20 ≈ MA60, ±2% 이내)
    """
    kospi_df = fetch_stock_data(market_index, period=90)

    ma20 = kospi_df['Close'].rolling(20).mean().iloc[-1]
    ma60 = kospi_df['Close'].rolling(60).mean().iloc[-1]

    diff_pct = (ma20 - ma60) / ma60

    if diff_pct > 0.02:
        return 'BULL'
    elif diff_pct < -0.02:
        return 'BEAR'
    else:
        return 'SIDEWAYS'

# 매수 점수 조정
market_trend = analyze_market_trend()
if market_trend == 'BEAR':
    if buy_score < 80:  # 강력 매수 신호가 아니면
        buy_score *= 0.5  # 50% 감점
    recommendation += " [⚠️ 하락장]"
elif market_trend == 'BULL':
    buy_score *= 1.1  # 10% 가산점
    recommendation += " [📈 상승장]"
```

**검증 방법**:
- 2023년 하락장, 2024년 상승장 데이터로 백테스트
- 시장 필터 적용 전/후 수익률 비교

#### 2.2 시장 변동성 지수 (VIX 개념)
**Priority**: P2

**요구사항**:
- KOSPI의 변동성 지수 계산
- 높은 변동성 시기에 리스크 경고

**기술 사양**:
```python
def calculate_market_volatility(market_index='KS11', period=20):
    """
    시장 변동성 계산 (VIX 유사)

    Returns:
        'LOW': 안정적
        'MEDIUM': 보통
        'HIGH': 고변동성 (위험)
    """
    kospi_df = fetch_stock_data(market_index, period=60)
    returns = kospi_df['Close'].pct_change()
    volatility = returns.rolling(period).std().iloc[-1]

    if volatility < 0.01:
        return 'LOW'
    elif volatility > 0.02:
        return 'HIGH'
    else:
        return 'MEDIUM'

# 고변동성 경고
market_volatility = calculate_market_volatility()
if market_volatility == 'HIGH':
    recommendation += " [⚠️ 시장 고변동성]"
    # 리스크 조정
    position_size_multiplier = 0.5  # 포지션 크기 축소
```

---

### 3. 손절 로직 강화

#### 3.1 매도 신호에 손절 로직 통합
**Priority**: P0 (최우선)

**요구사항**:
- 현재 손절가 계산은 매수 분석에만 존재
- 매도 분석에서도 손절 판단 수행
- 손실률이 기준 초과 시 즉시 손절 신호

**기술 사양**:
```python
# sell_signals.py의 analyze_sell_signals 메서드에 추가

def analyze_sell_signals(self, df: pd.DataFrame, buy_price: Optional[float] = None):
    # ... 기존 코드 ...

    # 손절 로직 추가
    if buy_price is not None:
        current_price = df['Close'].iloc[-1]
        loss_rate = (current_price - buy_price) / buy_price

        # 손절가 도달 (기본 -7%)
        if loss_rate <= -0.07:
            result['stop_loss_triggered'] = True
            result['stop_loss_message'] = f"손절가 도달 ({loss_rate*100:.1f}%)"
            # 매도 점수를 100으로 강제 설정
            result['sell_score'] = 100
            sell_signals.append(f"손절 발동 ({loss_rate*100:.1f}%)")
        else:
            result['stop_loss_triggered'] = False

    # ... 나머지 코드 ...
```

**검증 방법**:
- 실제 손실 케이스 시나리오 테스트
- 손절 신호가 최우선 순위로 표시되는지 확인

#### 3.2 동적 손절가 (Trailing Stop)
**Priority**: P1

**요구사항**:
- 수익이 발생하면 손절가를 상향 조정
- 최대 수익의 일정 비율 이하로 떨어지면 매도

**기술 사양**:
```python
def calculate_trailing_stop(buy_price: float, current_price: float,
                            highest_price: float, trailing_pct: float = 0.10):
    """
    추적 손절가 계산

    Args:
        buy_price: 매수가
        current_price: 현재가
        highest_price: 보유 기간 중 최고가
        trailing_pct: 추적 비율 (기본 10%)

    Returns:
        trailing_stop_price: 추적 손절가
    """
    profit_rate = (highest_price - buy_price) / buy_price

    if profit_rate > 0:
        # 수익 중이면 최고가 대비 trailing_pct 하락 시 손절
        trailing_stop = highest_price * (1 - trailing_pct)
        # 기본 손절가보다 높으면 사용
        base_stop_loss = buy_price * 0.93  # -7%
        return max(trailing_stop, base_stop_loss)
    else:
        # 손실 중이면 기본 손절가 사용
        return buy_price * 0.93
```

---

### 4. 예외 처리 및 로깅 개선

#### 4.1 API 호출 예외 처리
**Priority**: P0 (최우선)

**요구사항**:
- FinanceDataReader API 호출 실패 시 재시도 로직
- 네트워크 오류, 데이터 없음 등 케이스별 처리
- 사용자에게 명확한 에러 메시지 제공

**기술 사양**:
```python
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def fetch_stock_data_with_retry(symbol: str, start_date: str, end_date: str,
                                max_retries: int = 3) -> Optional[pd.DataFrame]:
    """
    재시도 로직이 있는 주가 데이터 가져오기
    """
    for attempt in range(max_retries):
        try:
            df = fdr.DataReader(symbol, start_date, end_date)

            if df is None or df.empty:
                logger.warning(f"종목 {symbol}: 데이터 없음 (시도 {attempt + 1}/{max_retries})")
                time.sleep(1)  # 1초 대기 후 재시도
                continue

            logger.info(f"종목 {symbol}: 데이터 가져오기 성공 ({len(df)} 행)")
            return df

        except Exception as e:
            logger.error(f"종목 {symbol}: API 호출 실패 - {str(e)} (시도 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 지수 백오프
            else:
                logger.error(f"종목 {symbol}: 최대 재시도 횟수 초과")
                return None

    return None
```

#### 4.2 계산 오류 예외 처리
**Priority**: P0

**요구사항**:
- 지표 계산 시 NaN, Inf 값 처리
- 데이터 부족 시 안전한 기본값 반환
- Division by zero 방지

**기술 사양**:
```python
def safe_calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """안전한 RSI 계산"""
    try:
        if df is None or len(df) < period:
            logger.warning(f"RSI 계산 불가: 데이터 부족 (필요: {period}, 현재: {len(df) if df is not None else 0})")
            return pd.Series([50.0] * len(df)) if df is not None else pd.Series()

        rsi = ta.rsi(df['Close'], length=period)

        # NaN 값 처리
        rsi = rsi.fillna(50.0)  # 중립값으로 채움

        # 범위 검증 (0-100)
        rsi = rsi.clip(0, 100)

        return rsi

    except Exception as e:
        logger.error(f"RSI 계산 중 오류: {str(e)}")
        return pd.Series([50.0] * len(df)) if df is not None else pd.Series()

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """안전한 나눗셈"""
    if denominator == 0 or pd.isna(denominator):
        return default
    result = numerator / denominator
    if pd.isna(result) or np.isinf(result):
        return default
    return result
```

#### 4.3 로깅 시스템 구축
**Priority**: P1

**요구사항**:
- 주요 이벤트 로깅 (매수/매도 신호, 오류 등)
- 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR)
- 파일 로깅 및 콘솔 출력

**기술 사양**:
```python
# src/utils/logger.py (새 파일)
import logging
import os
from datetime import datetime

def setup_logger(name: str, log_file: str = None, level=logging.INFO):
    """로거 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 포매터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# 사용 예시
# from src.utils.logger import setup_logger
# logger = setup_logger(__name__, f'logs/analysis_{datetime.now().strftime("%Y%m%d")}.log')
```

---

## 🔄 변경 사항 요약

### 파일 수정
1. **src/indicators/price_levels.py**
   - ATR 계산 메서드 추가
   - 동적 임계값 계산 로직 추가
   - 변동성 등급 분류 추가

2. **src/indicators/buy_signals.py**
   - 동적 무릎 임계값 적용
   - 시장 필터 통합
   - 안전한 지표 계산 함수로 교체

3. **src/indicators/sell_signals.py**
   - 손절 로직 통합
   - Trailing stop 계산 추가
   - 안전한 지표 계산 함수로 교체

4. **src/analysis/analyzer.py**
   - 시장 추세 분석 메서드 추가
   - 점수 조정 로직 추가
   - 예외 처리 강화

5. **src/data/fetcher.py**
   - 재시도 로직 추가
   - 예외 처리 강화
   - 로깅 추가

### 신규 파일
1. **src/utils/logger.py**
   - 로깅 유틸리티

2. **src/utils/market_analyzer.py**
   - 시장 추세 분석
   - 시장 변동성 계산

---

## 🧪 테스트 요구사항

### 1. 단위 테스트
- [ ] ATR 계산 정확성 검증
- [ ] 동적 임계값 계산 검증
- [ ] 시장 추세 판단 로직 검증
- [ ] 손절 트리거 조건 검증
- [ ] 예외 처리 케이스 검증

### 2. 통합 테스트
- [ ] 전체 분석 파이프라인 실행
- [ ] 여러 종목 동시 분석 (10종목 이상)
- [ ] API 실패 시나리오 테스트
- [ ] 데이터 부족 시나리오 테스트

### 3. 시나리오 테스트
**시나리오 1: 하락장에서의 매수 신호**
- KOSPI 하락장 + 개별 종목 매수 신호
- 기대 결과: 매수 점수 감점, 경고 메시지

**시나리오 2: 고변동성 종목**
- 바이오 종목 등 변동성 높은 종목
- 기대 결과: 넓은 임계값 적용

**시나리오 3: 손절 트리거**
- 매수가 대비 -7% 이상 손실
- 기대 결과: 매도 점수 100, 손절 메시지

---

## 📊 성과 측정

### 정량적 지표
1. **에러 발생률**: 0% 목표
2. **API 호출 성공률**: 99% 이상
3. **계산 완료율**: 100%
4. **응답 시간**: 종목당 3초 이내

### 정성적 지표
1. **사용자 신뢰도**: 명확한 신호와 근거 제시
2. **리스크 관리**: 손절 신호의 적절성
3. **시장 적응성**: 시장 상황 반영도

---

## 🚀 배포 계획

### 1단계: 개발 환경 테스트 (3일)
- 기능 개발 완료
- 단위 테스트 통과
- 로컬 환경 검증

### 2단계: 스테이징 테스트 (4일)
- 실제 시장 데이터로 테스트
- 여러 시나리오 검증
- 성능 모니터링

### 3단계: 프로덕션 배포 (2일)
- 점진적 롤아웃
- 모니터링 및 피드백 수집
- 긴급 롤백 준비

---

## ⚠️ 리스크 및 대응

### 리스크 1: API 변경
**대응**: FinanceDataReader 버전 고정, 대체 데이터 소스 준비

### 리스크 2: 계산 오류
**대응**: 철저한 예외 처리, 안전한 기본값 제공

### 리스크 3: 성능 저하
**대응**: 캐싱 전략, 비동기 처리 고려

---

## 📚 참고 자료

1. **기술적 분석 이론**
   - "Technical Analysis of the Financial Markets" - John Murphy
   - "Evidence-Based Technical Analysis" - David Aronson

2. **ATR 활용**
   - Wilder, J. Welles. "New Concepts in Technical Trading Systems" (1978)

3. **시장 국면 분석**
   - "Market Wizards" - Jack Schwager
   - "Trend Following" - Michael Covel

---

## ✅ 체크리스트

### Phase 1 - Part 1 (Task 1.1-1.3) ✅ 완료
- [x] ATR 계산 기능 구현
- [x] 변동성 등급 분류 시스템 구현
- [x] 동적 무릎/어깨 임계값 구현
- [x] JSON 리포트 생성기 업데이트
- [x] 웹 대시보드 UI 업데이트
- [x] NumPy 타입 직렬화 버그 수정
- [x] 문서 업데이트 (CLAUDE.md, CHANGELOG.md, TODO.md, PRD.md)
- [ ] 단위 테스트 작성 (다음 단계)

### Phase 1 - 남은 작업
- [ ] 시장 필터 추가 (Task 2.1-2.4)
- [ ] 손절 로직 강화 (Task 3.1-3.3)
- [ ] 예외 처리 및 로깅 개선 (Task 4.1-4.5)
- [ ] 단위 테스트 작성 및 통과
- [ ] 통합 테스트 통과
- [ ] 코드 리뷰 완료
- [ ] 배포 준비 완료

---

**Progress**: 15% (3/20 tasks completed - Week 1)
**Last Updated**: 2025-10-16 15:45
**Status**: 🚀 In Progress
