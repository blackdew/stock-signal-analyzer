# Phase 1 개선사항 TODO

> **목표 완료일**: 2주 이내 (2025-10-30)
> **현재 상태**: 📋 계획 단계

---

## 📅 일정 개요

```
Week 1 (10/16 - 10/22): 핵심 기능 개발
Week 2 (10/23 - 10/30): 테스트 및 배포
```

---

## 🔥 Week 1: 핵심 기능 개발

### Day 1-2 (10/16-10/17): 변동성 기반 동적 임계값

#### 📌 Task 1.1: ATR 계산 기능 추가 ✅
- [x] `src/indicators/price_levels.py`에 ATR 계산 메서드 추가
  ```python
  def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series
  ```
- [x] High, Low, Close 데이터 확인 및 전처리
- [x] pandas_ta의 `ta.atr()` 활용
- [x] NaN 값 처리 로직 추가
- [x] 변동성 등급 분류 기능 추가 (`calculate_volatility_level()`)
- [ ] 단위 테스트 작성 (다음 단계)
  - 정상 케이스: 충분한 데이터
  - 엣지 케이스: 데이터 부족 (14일 미만)
  - 예외 케이스: None, 빈 DataFrame

**담당**: 개발자
**실제 시간**: 3시간
**완료일**: 2025-10-16
**완료 조건**: ✅ ATR 계산이 정확하고 예외 처리가 완료됨

---

#### 📌 Task 1.2: 동적 무릎 임계값 계산 ✅
- [x] `is_at_knee()` 메서드 수정
  - 기존: `knee_threshold` 고정값 사용
  - 변경: ATR 기반 동적 계산
- [x] 동적 임계값 계산 로직
  ```python
  atr = self.calculate_atr(df)
  current_atr = atr.iloc[-1]
  floor_price = levels['floor']
  dynamic_knee = floor_price + (current_atr * 2 * adjustment_factor)
  ```
- [x] 변동성 등급 분류 추가
  - LOW: ATR < 평균의 70%
  - MEDIUM: 평균의 70-130%
  - HIGH: ATR > 평균의 130%
- [x] 등급별 조정 계수 적용
  ```python
  adjustment = {'LOW': 0.8, 'MEDIUM': 1.0, 'HIGH': 1.3}
  final_threshold = dynamic_knee * adjustment[level]
  ```
- [x] 웹 대시보드에 변동성 정보 표시
- [ ] 단위 테스트 작성 (다음 단계)

**담당**: 개발자
**실제 시간**: 2시간
**완료일**: 2025-10-16
**완료 조건**: ✅ 종목별로 다른 무릎 임계값이 계산됨

---

#### 📌 Task 1.3: 동적 어깨 임계값 계산 ✅
- [x] `is_at_shoulder()` 메서드 수정
- [x] ATR 기반 동적 어깨 임계값 계산
  ```python
  ceiling_price = levels['ceiling']
  dynamic_shoulder = ceiling_price - (current_atr * 2 * adjustment_factor)
  ```
- [x] 변동성 등급별 조정 적용
- [x] JSON 리포트 생성기에 변동성 정보 직렬화
- [x] NumPy boolean 타입 JSON 직렬화 버그 수정
- [ ] 단위 테스트 작성 (다음 단계)

**담당**: 개발자
**실제 시간**: 2시간
**완료일**: 2025-10-16
**완료 조건**: ✅ 종목별로 다른 어깨 임계값이 계산됨

---

### Day 3-4 (10/18-10/19): 시장 필터 추가

#### 📌 Task 2.1: 시장 분석 유틸리티 모듈 생성 ✅
- [x] 새 파일 생성: `src/utils/market_analyzer.py`
- [x] MarketAnalyzer 클래스 구현
  ```python
  class MarketAnalyzer:
      def __init__(self, market_index: str = 'KS11'):
          self.market_index = market_index

      def analyze_trend(self) -> str:
          """BULL/BEAR/SIDEWAYS 반환"""

      def calculate_volatility(self) -> str:
          """LOW/MEDIUM/HIGH 반환"""
  ```
- [x] FinanceDataReader로 KOSPI 데이터 가져오기
- [x] MA20/MA60 기반 추세 판단 로직
- [x] 1시간 캐싱 기능 추가 (성능 최적화)
- [x] 싱글톤 패턴 구현 (get_market_analyzer)
- [ ] 단위 테스트 작성 (다음 단계)

**담당**: 개발자
**실제 시간**: 2시간
**완료일**: 2025-10-16
**완료 조건**: ✅ KOSPI 추세를 정확히 판단함

---

#### 📌 Task 2.2: 매수 신호에 시장 필터 통합 ✅
- [x] `src/indicators/buy_signals.py` 수정
- [x] `analyze_buy_signals()`에 시장 추세 파라미터 추가
  ```python
  def analyze_buy_signals(
      self,
      df: pd.DataFrame,
      market_trend: str = 'UNKNOWN'  # 추가
  ) -> Dict[str, any]:
  ```
- [x] 시장 필터 로직 추가
  ```python
  # 하락장 페널티
  if market_trend == 'BEAR' and score < 80:
      market_adjusted_score = score * 0.5
      buy_signals.append("⚠️ 시장 하락장 - 매수 신중")

  # 상승장 보너스
  elif market_trend == 'BULL':
      market_adjusted_score = score * 1.1
      buy_signals.append("📈 시장 상승장 - 매수 유리")
  ```
- [x] 추천 메시지에 시장 상태 표시
- [x] market_adjusted_score 반환값 추가
- [ ] 통합 테스트 작성 (다음 단계)

**담당**: 개발자
**실제 시간**: 2시간
**완료일**: 2025-10-16
**완료 조건**: ✅ 시장 상황에 따라 매수 점수가 조정됨

---

#### 📌 Task 2.3: 매도 신호에 시장 필터 통합 ✅
- [x] `src/indicators/sell_signals.py` 수정
- [x] `analyze_sell_signals()`에 시장 추세 파라미터 추가
- [x] 시장 필터 로직 추가
  ```python
  # 상승장에서는 매도 점수 감점 (30%)
  if market_trend == 'BULL' and score < 80:
      market_adjusted_score = score * 0.7
      sell_signals.append("📈 시장 상승장 - 매도 신중")

  # 하락장에서는 매도 점수 가점 (20%)
  elif market_trend == 'BEAR':
      market_adjusted_score = score * 1.2
      sell_signals.append("⚠️ 시장 하락장 - 매도 고려")
  ```
- [x] market_adjusted_score 반환값 추가
- [ ] 통합 테스트 작성 (다음 단계)

**담당**: 개발자
**실제 시간**: 2시간
**완료일**: 2025-10-16
**완료 조건**: ✅ 시장 상황에 따라 매도 점수가 조정됨

---

#### 📌 Task 2.4: Analyzer에 시장 분석 통합 ✅
- [x] `src/analysis/analyzer.py` 수정
- [x] `__init__`에 MarketAnalyzer 인스턴스 추가
  ```python
  from src.utils.market_analyzer import get_market_analyzer
  self.market_analyzer = get_market_analyzer()
  ```
- [x] `analyze_stock()` 메서드 수정
  ```python
  # 시장 추세 분석
  market_trend = self.market_analyzer.analyze_trend()
  market_summary = self.market_analyzer.get_market_summary()

  # 매수/매도 분석에 전달
  buy_analysis = self.buy_analyzer.analyze_buy_signals(df, market_trend)
  sell_analysis = self.sell_analyzer.analyze_sell_signals(df, buy_price, market_trend)
  ```
- [x] JSON 리포트 생성기에 market_summary 직렬화 추가
- [x] 웹 대시보드에 시장 정보 표시
- [ ] 통합 테스트 (다음 단계)

**담당**: 개발자
**실제 시간**: 2.5시간
**완료일**: 2025-10-16
**완료 조건**: ✅ 전체 분석 파이프라인에 시장 필터 적용됨

---

### Day 5-6 (10/20-10/21): 손절 로직 강화

#### 📌 Task 3.1: 매도 신호에 손절 로직 추가
- [ ] `src/indicators/sell_signals.py` 수정
- [ ] `analyze_sell_signals()` 메서드에 손절 로직 추가
  ```python
  # 손절 체크
  if buy_price is not None:
      loss_rate = (current_price - buy_price) / buy_price

      if loss_rate <= -self.stop_loss_pct:  # 기본 -7%
          result['stop_loss_triggered'] = True
          result['sell_score'] = 100  # 최고 우선순위
          sell_signals.insert(0, f"🚨 손절 발동 ({loss_rate*100:.1f}%)")
  ```
- [ ] 추천 메시지에 손절 우선 표시
  ```python
  if analysis.get('stop_loss_triggered'):
      return f"🚨 즉시 손절 ({loss_rate*100:.1f}%)"
  ```
- [ ] 단위 테스트 작성
  - 손절 트리거 케이스
  - 손절 미트리거 케이스

**담당**: 개발자
**예상 시간**: 3시간
**완료 조건**: 손실 시 명확한 손절 신호 제공

---

#### 📌 Task 3.2: Trailing Stop 구현
- [ ] `calculate_trailing_stop()` 메서드 추가
  ```python
  def calculate_trailing_stop(
      self,
      buy_price: float,
      current_price: float,
      highest_price: float,
      trailing_pct: float = 0.10
  ) -> Dict[str, any]:
  ```
- [ ] 로직 구현
  ```python
  profit_rate = (highest_price - buy_price) / buy_price

  if profit_rate > 0:
      # 수익 중: 최고가 대비 trailing_pct 하락 시 손절
      trailing_stop = highest_price * (1 - trailing_pct)
      base_stop = buy_price * (1 - self.stop_loss_pct)
      final_stop = max(trailing_stop, base_stop)
  else:
      # 손실 중: 기본 손절가
      final_stop = buy_price * (1 - self.stop_loss_pct)

  return {
      'trailing_stop_price': final_stop,
      'is_trailing': profit_rate > 0,
      'stop_type': 'TRAILING' if profit_rate > 0 else 'FIXED'
  }
  ```
- [ ] `analyze_sell_signals()`에 통합
- [ ] 단위 테스트 작성

**담당**: 개발자
**예상 시간**: 4시간
**완료 조건**: 수익 중 하락 시 trailing stop 작동

---

#### 📌 Task 3.3: 최고가 추적 기능 추가
- [ ] 포트폴리오 CSV에 최고가 컬럼 추가 옵션
  ```csv
  종목코드,매수가격,수량,종목명,보유중최고가
  005930,71000,150,삼성전자,75000
  ```
- [ ] 최고가 없으면 현재가를 최고가로 사용
- [ ] Trailing stop 계산 시 활용
- [ ] 문서 업데이트 (README, CLAUDE.md)

**담당**: 개발자
**예상 시간**: 2시간
**완료 조건**: 최고가 기반 trailing stop 작동

---

### Day 7 (10/22): 예외 처리 및 로깅

#### 📌 Task 4.1: 로깅 유틸리티 생성
- [ ] 새 파일 생성: `src/utils/logger.py`
- [ ] `setup_logger()` 함수 구현
  ```python
  def setup_logger(
      name: str,
      log_file: str = None,
      level=logging.INFO
  ) -> logging.Logger:
  ```
- [ ] 콘솔 + 파일 핸들러 설정
- [ ] 포매터 설정 (시간, 레벨, 메시지)
- [ ] logs 디렉토리 자동 생성
- [ ] 단위 테스트

**담당**: 개발자
**예상 시간**: 2시간
**완료 조건**: 로거 생성 및 로그 파일 저장 확인

---

#### 📌 Task 4.2: API 호출 재시도 로직
- [ ] `src/data/fetcher.py` 수정
- [ ] `fetch_stock_data()` 메서드에 재시도 로직 추가
  ```python
  def fetch_stock_data_with_retry(
      self,
      symbol: str,
      start_date: str,
      end_date: str,
      max_retries: int = 3
  ) -> Optional[pd.DataFrame]:
  ```
- [ ] 지수 백오프 (exponential backoff) 구현
  ```python
  for attempt in range(max_retries):
      try:
          df = fdr.DataReader(symbol, start_date, end_date)
          if df is not None and not df.empty:
              logger.info(f"종목 {symbol}: 데이터 가져오기 성공")
              return df
      except Exception as e:
          logger.error(f"시도 {attempt+1} 실패: {e}")
          time.sleep(2 ** attempt)  # 1초, 2초, 4초 대기

      return None
  ```
- [ ] 에러 케이스별 처리
  - 네트워크 오류: 재시도
  - 종목 코드 오류: 즉시 실패
  - 데이터 없음: 경고 로그
- [ ] 단위 테스트 (모킹 사용)

**담당**: 개발자
**예상 시간**: 3시간
**완료 조건**: API 실패 시 자동 재시도 작동

---

#### 📌 Task 4.3: 안전한 지표 계산 함수
- [ ] `src/indicators/buy_signals.py` 수정
- [ ] `calculate_rsi()` → `safe_calculate_rsi()` 변경
  ```python
  def safe_calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
      try:
          if df is None or len(df) < self.rsi_period:
              logger.warning("RSI 계산 불가: 데이터 부족")
              return pd.Series([50.0] * len(df))

          rsi = ta.rsi(df['Close'], length=self.rsi_period)
          rsi = rsi.fillna(50.0)  # NaN → 중립값
          rsi = rsi.clip(0, 100)  # 범위 검증
          return rsi

      except Exception as e:
          logger.error(f"RSI 계산 오류: {e}")
          return pd.Series([50.0] * len(df))
  ```
- [ ] 모든 지표 계산에 동일한 패턴 적용
  - `check_volume_surge()`
  - `check_golden_cross()`
  - `calculate_atr()`
- [ ] `src/indicators/sell_signals.py`에도 동일 적용
- [ ] 단위 테스트

**담당**: 개발자
**예상 시간**: 4시간
**완료 조건**: 모든 계산이 안전하게 예외 처리됨

---

#### 📌 Task 4.4: Division by zero 방지
- [ ] 유틸리티 함수 생성: `src/utils/helpers.py`
  ```python
  def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
      """안전한 나눗셈"""
      if denominator == 0 or pd.isna(denominator):
          return default

      result = numerator / denominator

      if pd.isna(result) or np.isinf(result):
          return default

      return result
  ```
- [ ] 모든 나눗셈 연산에 적용
  - 수익률 계산
  - 상승률 계산
  - 변동성 계산
- [ ] 단위 테스트

**담당**: 개발자
**예상 시간**: 2시간
**완료 조건**: ZeroDivisionError 발생 안 함

---

#### 📌 Task 4.5: 전체 모듈에 로깅 추가
- [ ] 각 모듈에 로거 추가
  ```python
  from src.utils.logger import setup_logger
  logger = setup_logger(__name__)
  ```
- [ ] 주요 이벤트 로깅
  - INFO: 분석 시작/완료, 신호 발생
  - WARNING: 데이터 부족, API 지연
  - ERROR: 계산 오류, API 실패
  - DEBUG: 상세 계산 과정
- [ ] main.py에서 로그 레벨 설정 옵션 추가
  ```bash
  uv run main.py --log-level DEBUG
  ```

**담당**: 개발자
**예상 시간**: 3시간
**완료 조건**: 모든 주요 이벤트가 로그에 기록됨

---

## 🧪 Week 2: 테스트 및 배포

### Day 8-9 (10/23-10/24): 단위 테스트

#### 📌 Task 5.1: 테스트 환경 설정
- [ ] 테스트 디렉토리 생성: `tests/`
  ```
  tests/
  ├── __init__.py
  ├── test_price_levels.py
  ├── test_buy_signals.py
  ├── test_sell_signals.py
  ├── test_analyzer.py
  └── test_market_analyzer.py
  ```
- [ ] pytest 설치
  ```bash
  uv add pytest pytest-cov --dev
  ```
- [ ] 테스트 픽스처 생성 (샘플 데이터)
  ```python
  @pytest.fixture
  def sample_stock_data():
      # 180일 샘플 주가 데이터 생성
      pass
  ```

**담당**: 개발자
**예상 시간**: 2시간
**완료 조건**: pytest 실행 환경 준비 완료

---

#### 📌 Task 5.2: 가격 레벨 테스트
- [ ] `tests/test_price_levels.py` 작성
- [ ] ATR 계산 테스트
  ```python
  def test_calculate_atr_normal():
      # 정상 케이스
      pass

  def test_calculate_atr_insufficient_data():
      # 데이터 부족 케이스
      pass

  def test_calculate_atr_nan_values():
      # NaN 값 포함 케이스
      pass
  ```
- [ ] 동적 무릎/어깨 임계값 테스트
  ```python
  def test_dynamic_knee_threshold():
      # 변동성별 임계값 차이 검증
      pass
  ```
- [ ] 커버리지 80% 이상

**담당**: 개발자
**예상 시간**: 4시간
**완료 조건**: 모든 테스트 통과

---

#### 📌 Task 5.3: 매수/매도 신호 테스트
- [ ] `tests/test_buy_signals.py` 작성
  - RSI 계산 테스트
  - 거래량 급증 판단 테스트
  - 골든크로스 감지 테스트
  - 시장 필터 적용 테스트
  - 점수 계산 테스트
- [ ] `tests/test_sell_signals.py` 작성
  - 손절 트리거 테스트
  - Trailing stop 계산 테스트
  - 매도 전략 추천 테스트
- [ ] 커버리지 80% 이상

**담당**: 개발자
**예상 시간**: 6시간
**완료 조건**: 모든 테스트 통과

---

#### 📌 Task 5.4: 시장 분석 테스트
- [ ] `tests/test_market_analyzer.py` 작성
- [ ] 추세 판단 테스트
  ```python
  def test_bull_market():
      # MA20 > MA60 케이스
      pass

  def test_bear_market():
      # MA20 < MA60 케이스
      pass

  def test_sideways_market():
      # MA20 ≈ MA60 케이스
      pass
  ```
- [ ] 변동성 계산 테스트
- [ ] 커버리지 90% 이상

**담당**: 개발자
**예상 시간**: 3시간
**완료 조건**: 모든 테스트 통과

---

#### 📌 Task 5.5: 통합 테스트
- [ ] `tests/test_analyzer.py` 작성
- [ ] 전체 분석 파이프라인 테스트
  ```python
  def test_full_analysis_pipeline():
      # 여러 종목 동시 분석
      symbols = ['005930', '000660', '035420']
      results = analyzer.analyze_multiple_stocks(symbols, ...)
      assert len(results) == 3
      # 각 결과 검증
      pass
  ```
- [ ] API 모킹 테스트
  ```python
  @mock.patch('FinanceDataReader.DataReader')
  def test_api_failure_retry(mock_fdr):
      # API 실패 → 재시도 → 성공 시나리오
      pass
  ```

**담당**: 개발자
**예상 시간**: 4시간
**완료 조건**: 통합 테스트 통과

---

### Day 10-11 (10/25-10/26): 시나리오 테스트

#### 📌 Task 6.1: 하락장 시나리오 테스트
- [ ] 테스트 데이터 준비
  - 2023년 하락장 기간 데이터
  - KOSPI MA20 < MA60
- [ ] 개별 종목 매수 신호 + 하락장 필터 검증
  ```python
  def test_buy_signal_in_bear_market():
      # 매수 점수 감점 확인
      # 경고 메시지 확인
      pass
  ```
- [ ] 실제 수익률 시뮬레이션 (간단한 백테스트)
- [ ] 결과 문서화

**담당**: 개발자, QA
**예상 시간**: 4시간
**완료 조건**: 하락장에서 안전한 신호 확인

---

#### 📌 Task 6.2: 고변동성 종목 테스트
- [ ] 고변동성 종목 선정 (바이오, 테마주 등)
- [ ] 동적 임계값 적용 확인
  ```python
  def test_high_volatility_stock():
      # 바이오 종목
      # ATR 기반 넓은 임계값 확인
      pass
  ```
- [ ] 저변동성 종목과 비교
- [ ] 결과 문서화

**담당**: 개발자, QA
**예상 시간**: 3시간
**완료 조건**: 종목별로 다른 임계값 적용 확인

---

#### 📌 Task 6.3: 손절 시나리오 테스트
- [ ] 손실 종목 시나리오
  - 매수가: 100,000원
  - 현재가: 93,000원 (-7%)
- [ ] 손절 신호 확인
  ```python
  def test_stop_loss_trigger():
      # 손절 트리거 확인
      # 매도 점수 100 확인
      # 메시지 확인
      pass
  ```
- [ ] Trailing stop 시나리오
  - 매수가: 100,000원
  - 최고가: 120,000원
  - 현재가: 108,000원 (최고가 대비 -10%)
- [ ] Trailing stop 트리거 확인
- [ ] 결과 문서화

**담당**: 개발자, QA
**예상 시간**: 3시간
**완료 조건**: 손절 로직 정확히 작동

---

#### 📌 Task 6.4: 엣지 케이스 테스트
- [ ] 데이터 부족 케이스
  - 신규 상장 종목 (60일 미만 데이터)
  - 기대 결과: 안전한 기본값, 에러 없음
- [ ] API 실패 케이스
  - 네트워크 오류
  - 잘못된 종목 코드
  - 기대 결과: 재시도 후 명확한 에러 메시지
- [ ] 극단적 값 케이스
  - 거래 정지 종목 (거래량 0)
  - 상한가/하한가 종목
- [ ] 결과 문서화

**담당**: 개발자, QA
**예상 시간**: 4시간
**완료 조건**: 모든 엣지 케이스 안전하게 처리

---

### Day 12-13 (10/27-10/28): 성능 및 문서화

#### 📌 Task 7.1: 성능 테스트
- [ ] 10종목 동시 분석 속도 측정
  - 목표: 종목당 3초 이내
- [ ] 병목 지점 확인 (프로파일링)
  ```bash
  python -m cProfile -o profile.stats main.py
  ```
- [ ] 최적화 필요 시 개선
  - 캐싱 추가
  - 중복 계산 제거
- [ ] 성능 리포트 작성

**담당**: 개발자
**예상 시간**: 3시간
**완료 조건**: 목표 성능 달성

---

#### 📌 Task 7.2: 메모리 사용량 테스트
- [ ] 메모리 프로파일링
  ```bash
  mprof run main.py --symbols 005930 000660 ...
  mprof plot
  ```
- [ ] 메모리 누수 확인
- [ ] 대용량 데이터 처리 테스트 (100종목)
- [ ] 최적화 필요 시 개선

**담당**: 개발자
**예상 시간**: 2시간
**완료 조건**: 메모리 안정적 사용

---

#### 📌 Task 7.3: 문서 업데이트
- [ ] README.md 수정
  - Phase 1 변경사항 추가
  - 새로운 기능 설명
  - 사용 예시 추가
- [ ] CLAUDE.md 수정
  - 프로젝트 구조 업데이트
  - 새로운 모듈 설명
- [ ] API 문서 작성 (docstring)
  - 모든 public 메서드에 docstring 추가
  - 파라미터, 반환값, 예외 설명
- [ ] 변경 로그 작성: `docs/phase-001/CHANGELOG.md`

**담당**: 개발자
**예상 시간**: 4시간
**완료 조건**: 문서 완성도 100%

---

#### 📌 Task 7.4: 사용자 가이드 작성
- [ ] `docs/phase-001/USER_GUIDE.md` 작성
- [ ] 새로운 기능 사용법 설명
  - 동적 임계값 확인 방법
  - 시장 필터 이해하기
  - 손절 신호 대응 방법
- [ ] FAQ 섹션 추가
  - Q: 임계값이 종목마다 다른 이유는?
  - Q: 하락장에서 매수 신호가 안 나오는 이유는?
  - Q: Trailing stop이란?
- [ ] 스크린샷 추가 (웹 대시보드)

**담당**: 개발자
**예상 시간**: 3시간
**완료 조건**: 사용자 가이드 완성

---

### Day 14 (10/29-10/30): 배포 및 모니터링

#### 📌 Task 8.1: 배포 전 체크리스트
- [ ] 모든 단위 테스트 통과
  ```bash
  pytest tests/ -v --cov=src --cov-report=html
  ```
- [ ] 코드 커버리지 80% 이상 확인
- [ ] 통합 테스트 통과
- [ ] 시나리오 테스트 통과
- [ ] 문서 최종 검토
- [ ] 코드 리뷰 완료
- [ ] 의존성 버전 고정
  ```bash
  uv pip freeze > requirements.txt
  ```

**담당**: 개발자, 리드
**예상 시간**: 2시간
**완료 조건**: 모든 체크리스트 완료

---

#### 📌 Task 8.2: 배포
- [ ] 기존 백업 생성
  ```bash
  git checkout -b backup-before-phase1
  git push origin backup-before-phase1
  ```
- [ ] Phase 1 브랜치 병합
  ```bash
  git checkout main
  git merge phase-001
  ```
- [ ] 버전 태그 생성
  ```bash
  git tag -a v1.1.0 -m "Phase 1: Dynamic thresholds, market filters, stop loss"
  git push origin v1.1.0
  ```
- [ ] 프로덕션 배포
- [ ] 롤백 계획 준비

**담당**: 개발자, DevOps
**예상 시간**: 1시간
**완료 조건**: 배포 완료

---

#### 📌 Task 8.3: 모니터링 설정
- [ ] 로그 모니터링 설정
  - 에러 로그 실시간 추적
  - 경고 로그 알림 설정
- [ ] 성능 모니터링
  - API 호출 성공률 추적
  - 분석 완료 시간 추적
- [ ] 사용자 피드백 수집 채널 준비
  - GitHub Issues 템플릿
  - 피드백 양식
- [ ] 대시보드 설정 (선택사항)
  ```python
  # 간단한 통계 수집
  {
    "total_analysis": 100,
    "api_success_rate": 0.99,
    "avg_analysis_time": 2.3,
    "error_count": 1
  }
  ```

**담당**: 개발자, DevOps
**예상 시간**: 2시간
**완료 조건**: 모니터링 활성화

---

#### 📌 Task 8.4: 사용자 공지
- [ ] 릴리스 노트 작성
  ```markdown
  # v1.1.0 Release Notes

  ## 🎉 Phase 1 개선사항

  ### 주요 변경사항
  1. 변동성 기반 동적 임계값
  2. 시장 필터 추가
  3. 손절 로직 강화
  4. 예외 처리 개선

  ### 사용자 영향
  - 종목별로 더 정확한 매매 신호
  - 시장 상황 고려한 추천
  - 안정적인 손절 신호

  ### 업그레이드 방법
  ...
  ```
- [ ] GitHub Release 생성
- [ ] 사용자 공지 (README 배너, 이메일 등)
- [ ] 피드백 요청

**담당**: PM, 개발자
**예상 시간**: 1시간
**완료 조건**: 사용자 공지 완료

---

## 📊 진행 상황 추적

### 전체 진행률
```
[███████             ] 35% (7/20 완료 - Week 1만 계산)
```

### 주차별 진행률
- **Week 1 (핵심 기능)**: [███████░░░] 35% (7/20 완료)
  - ✅ Task 1.1: ATR 계산 기능 추가
  - ✅ Task 1.2: 동적 무릎 임계값 계산
  - ✅ Task 1.3: 동적 어깨 임계값 계산
  - ✅ Task 2.1: 시장 분석 유틸리티 모듈 생성
  - ✅ Task 2.2: 매수 신호에 시장 필터 통합
  - ✅ Task 2.3: 매도 신호에 시장 필터 통합
  - ✅ Task 2.4: Analyzer에 시장 분석 통합
- **Week 2 (테스트/배포)**: [ ] 0% (0/20 완료)

### 우선순위별 진행률
- **P0 (최우선)**: [███████░░░] 70% (완료: 1.1, 1.2, 1.3 중 일부)
- **P1 (높음)**: [ ] 0% (0/8 완료)
- **P2 (보통)**: [ ] 0% (0/2 완료)

---

## ⚠️ 블로커 및 이슈

> 진행 중 발생하는 블로커와 이슈를 기록합니다.

### 블로커 (작업 중단)
_현재 없음_

### 이슈 (주의 필요)
_현재 없음_

---

## 📝 일일 리포트

### 2025-10-16 (Day 1-3)
- **완료**: ✅ Task 1.1, 1.2, 1.3 (변동성 기반 동적 임계값), Task 2.1, 2.2, 2.3, 2.4 (시장 필터 추가)
- **진행 중**: 문서 업데이트
- **주요 성과**:
  - ATR 계산 및 변동성 등급 분류 구현
  - 동적 무릎/어깨 임계값 구현
  - 웹 대시보드에 변동성 정보 시각화
  - NumPy boolean 직렬화 버그 수정
  - MarketAnalyzer 모듈 생성 (KOSPI 추세 분석)
  - 매수/매도 신호에 시장 필터 통합 (상승장/하락장 점수 조정)
  - 전체 분석 파이프라인에 시장 분석 통합
  - 웹 대시보드에 시장 정보 카드 추가
- **다음 계획**: Task 3.1-3.3 (손절 로직 강화)
- **블로커**: 없음
- **소요 시간**: 약 15.5시간 (계획: 22시간 → 70% 효율)
- **진행률**: Week 1 35% 완료 (7/20 태스크)

---

## ✅ 최종 체크리스트

### 기능 개발
- [ ] 변동성 기반 동적 임계값 구현
- [ ] 시장 필터 추가
- [ ] 손절 로직 강화
- [ ] 예외 처리 및 로깅 개선

### 테스트
- [ ] 단위 테스트 작성 및 통과
- [ ] 통합 테스트 통과
- [ ] 시나리오 테스트 통과
- [ ] 성능 테스트 통과

### 문서
- [ ] README.md 업데이트
- [ ] CLAUDE.md 업데이트
- [ ] 사용자 가이드 작성
- [ ] 릴리스 노트 작성

### 배포
- [ ] 배포 전 체크리스트 완료
- [ ] 프로덕션 배포
- [ ] 모니터링 설정
- [ ] 사용자 공지

---

## 🎯 성공 기준

Phase 1은 다음 조건을 **모두** 만족할 때 완료로 간주합니다:

1. ✅ **기능 완성도**: 모든 P0, P1 태스크 완료
2. ✅ **품질**: 코드 커버리지 80% 이상, 모든 테스트 통과
3. ✅ **성능**: 종목당 분석 시간 3초 이내
4. ✅ **안정성**: 에러 발생률 0%, API 성공률 99% 이상
5. ✅ **문서**: 사용자 가이드 및 API 문서 완성
6. ✅ **배포**: 프로덕션 배포 및 모니터링 활성화

---

**Last Updated**: 2025-10-16 18:00
**Status**: 🚀 진행 중 (Task 1.1-1.3, 2.1-2.4 완료, 35%)
**Next Review**: 2025-10-20 (Day 5)
