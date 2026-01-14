"""주식 신호 분석 앱 설정"""
from datetime import datetime, timedelta

# 분석할 종목 리스트 (종목 코드)
# 예: 삼성전자(005930), SK하이닉스(000660), NAVER(035420)
STOCK_SYMBOLS = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # NAVER
]

# 데이터 분석 기간 설정
ANALYSIS_PERIOD_DAYS = 180  # 최근 N일의 데이터 분석
START_DATE = (datetime.now() - timedelta(days=ANALYSIS_PERIOD_DAYS)).strftime("%Y-%m-%d")
END_DATE = datetime.now().strftime("%Y-%m-%d")

# 바닥/천장 감지 설정
FLOOR_CEILING_LOOKBACK = 60  # 바닥/천장 계산을 위한 lookback 기간 (일)

# 매수 신호 설정
BUY_KNEE_THRESHOLD = 0.15  # 바닥 대비 15% 상승을 "무릎"으로 정의
STOP_LOSS_PERCENTAGE = 0.07  # 손절가: 매수가 대비 -7%
CHASE_BUY_RISK_THRESHOLD = 0.25  # 바닥 대비 25% 이상 상승시 추격매수 위험

# 매도 신호 설정
SELL_SHOULDER_THRESHOLD = 0.15  # 천장 대비 15% 하락을 "어깨"로 정의
PROFIT_TARGET_FULL_SELL = 0.30  # 수익률 30% 이상이면 전량 매도 추천
PROFIT_TARGET_PARTIAL_SELL = 0.15  # 수익률 15% 이상이면 분할 매도 추천

# RSI 설정
RSI_PERIOD = 14
RSI_OVERSOLD = 30  # RSI가 이 값 이하면 과매도
RSI_OVERBOUGHT = 70  # RSI가 이 값 이상이면 과매수

# 이동평균선 설정
MA_SHORT = 20  # 단기 이동평균 (일)
MA_LONG = 60   # 장기 이동평균 (일)

# 거래량 설정
VOLUME_SURGE_MULTIPLIER = 2.0  # 평균 거래량 대비 2배 이상이면 급증으로 판단

# 액션 결정 임계값 설정
ACTION_BUY_THRESHOLD = 30  # 매수 신호로 분류하기 위한 최소 점수
ACTION_SELL_THRESHOLD = 30  # 매도 신호로 분류하기 위한 최소 점수
ACTION_SCORE_DIFF_THRESHOLD = 10  # 우위를 판단하기 위한 최소 점수 차이

# 보고서 저장 설정
import os
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

# 포트폴리오 파일 설정
DEFAULT_PORTFOLIO_FILE = os.path.join(PROJECT_ROOT, ".portfolio")
MYPORTFOLIO_DIR = os.path.join(PROJECT_ROOT, "myportfolio")

# ============================================
# 전고점 돌파 전략 설정
# ============================================

# 52주 신고가 설정
WEEK52_LOOKBACK_DAYS = 252  # 52주 = 약 252 거래일

# 전고점 근접 범위 (90% ~ 105%)
BREAKOUT_HIGH_RANGE_MIN = 0.90  # 52주 고점 대비 최소 비율
BREAKOUT_HIGH_RANGE_MAX = 1.05  # 52주 고점 대비 최대 비율

# 돌파 시도 설정
BREAKOUT_ATTEMPT_THRESHOLD = 0.95  # 95% 이상 도달 시 돌파 시도로 간주
BREAKOUT_ATTEMPT_LOOKBACK_DAYS = 60  # 최근 60일 내 시도 횟수 확인
BREAKOUT_MIN_ATTEMPT_COUNT = 3  # 최소 3회 이상 시도 시 돌파 확률 상승

# 유동성 필터
BREAKOUT_MIN_MARKET_CAP = 2000.0  # 최소 시가총액 (억원)
BREAKOUT_MIN_AVG_TRADING_VALUE = 50.0  # 최소 일평균 거래대금 (억원)

# 손절/매도 설정
BREAKOUT_STOP_LOSS_PCT = 0.05  # 절대 손절 -5%
BREAKOUT_TRAILING_STOP_MA = 20  # 상대 손절: MA20 이탈
