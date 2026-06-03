"""
Rubric Engine

투자 기회를 평가하기 위한 루브릭 시스템.
기술적 분석, 수급 분석, 펀더멘털 분석, 시장 환경 분석을 통합하여
종합 투자 점수를 산출합니다.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import RUBRIC_WEIGHTS, RUBRIC_WEIGHTS_V1, RUBRIC_WEIGHTS_V3, get_grade_from_score


# =============================================================================
# 퀀트 가치 투자 평가지표 산출 함수 (Piotroski, PEG, Valuation Band)
# =============================================================================


def calc_piotroski_f_score(yearly_history: Dict[str, List[float]]) -> int:
    """
    Piotroski F-Score 계산 (9점 만점)
    
    수익성(4점), 재무건전성(3점), 운영 효율성(2점)을 종합 평가하여 
    가치 함정(Value Trap) 우려를 차단합니다.
    """
    if not yearly_history:
        return 0

    score = 0
    try:
        net_inc = yearly_history.get("net_income", [])
        cfo = yearly_history.get("cfo", [])
        assets = yearly_history.get("assets", [])
        debt = yearly_history.get("debt_ratio", [])
        curr_ratio = yearly_history.get("current_ratio", [])
        cap = yearly_history.get("capital_stock", [])
        op_margin = yearly_history.get("operating_margin", [])
        rev = yearly_history.get("revenue", [])

        # 1. ROA > 0 (당기순이익 당해년도 양수)
        if len(net_inc) >= 3 and net_inc[2] is not None and net_inc[2] > 0:
            score += 1

        # 2. CFO > 0 (영업활동현금흐름 당해년도 양수)
        if len(cfo) >= 3 and cfo[2] is not None and cfo[2] > 0:
            score += 1

        # 3. Delta ROA > 0 (전년 대비 ROA 개선)
        if len(net_inc) >= 3 and len(assets) >= 3 and assets[1] > 0 and assets[2] > 0:
            roa_prev = net_inc[1] / assets[1]
            roa_curr = net_inc[2] / assets[2]
            if roa_curr > roa_prev:
                score += 1

        # 4. CFO > Net Income (영업활동현금흐름이 당기순이익보다 우수)
        if len(cfo) >= 3 and len(net_inc) >= 3 and cfo[2] is not None and net_inc[2] is not None:
            if cfo[2] >= net_inc[2]:
                score += 1

        # 5. Delta Leverage < 0 (부채비율 감소)
        if len(debt) >= 3 and debt[1] is not None and debt[2] is not None:
            if debt[2] < debt[1]:
                score += 1

        # 6. Delta Liquidity > 0 (유동비율 개선)
        if len(curr_ratio) >= 3 and curr_ratio[1] is not None and curr_ratio[2] is not None:
            if curr_ratio[2] > curr_ratio[1]:
                score += 1

        # 7. Eq_Issued = 0 (신주 발행 없음 / 자본금 증가 없음)
        if len(cap) >= 3 and cap[1] is not None and cap[2] is not None:
            if cap[2] <= cap[1]:
                score += 1

        # 8. Delta Operating Margin > 0 (영업이익률 마진 향상)
        if len(op_margin) >= 3 and op_margin[1] is not None and op_margin[2] is not None:
            if op_margin[2] > op_margin[1]:
                score += 1

        # 9. Delta Asset Turnover > 0 (자산회전율 개선)
        if len(rev) >= 3 and len(assets) >= 3 and assets[1] > 0 and assets[2] > 0:
            turn_prev = rev[1] / assets[1]
            turn_curr = rev[2] / assets[2]
            if turn_curr > turn_prev:
                score += 1

    except Exception:
        pass

    return score


def calc_peg_ratio(per: Optional[float], growth: Optional[float]) -> Tuple[float, float]:
    """
    PEG Ratio 계산 (PER / 영업이익 성장률 YoY) 및 스코어링 (10점 만점)
    
    성장률이 음수이거나 0일 때 발생 가능한 분모 오류 방지를 위한 Clamping 탑재.
    """
    if per is None or per <= 0 or growth is None or growth <= 0:
        return 1.0, 99.0

    peg = per / growth

    # 스코어링 (10점 만점)
    if peg <= 0.5:
        return 10.0, peg
    elif peg <= 1.0:
        return 8.0, peg
    elif peg <= 1.5:
        return 5.0, peg
    else:
        return 1.0, peg


def calc_valuation_band_score(
    current_val: Optional[float],
    val_min: Optional[float],
    val_max: Optional[float]
) -> float:
    """
    Valuation Band 내 현재 위치 분위수 계산 및 스코어링 (10점 만점)
    
    바닥권(0~20% 영역)에 가까울수록 만점(10점)에 근접하는 하방 경직 가치주 판정.
    """
    if None in (current_val, val_min, val_max) or val_max <= val_min:
        return 5.0

    percentile = (current_val - val_min) / (val_max - val_min)
    percentile = max(0.0, min(1.0, percentile))

    # 바닥에 있을수록 고득점
    score = (1.0 - percentile) * 10.0
    return round(max(0.0, min(10.0, score)), 2)


# =============================================================================
# 데이터 구조 정의
# =============================================================================



@dataclass
class CategoryScore:
    """카테고리별 점수"""

    name: str  # technical, supply, fundamental, market
    score: float  # 0-100 (정규화된 점수)
    max_score: int  # 해당 카테고리 만점 (가중치)
    weighted_score: float  # 가중치 적용 점수
    details: Dict[str, float] = field(default_factory=dict)  # 세부 항목별 점수


@dataclass
class RubricResult:
    """루브릭 평가 결과"""

    symbol: str
    name: str

    # 카테고리별 점수
    technical: CategoryScore
    supply: CategoryScore
    fundamental: CategoryScore
    market: CategoryScore

    # 신규 카테고리 (V2)
    risk: Optional[CategoryScore] = None              # 리스크 평가
    relative_strength: Optional[CategoryScore] = None  # 상대 강도

    # V3 카테고리 (8대 핵심 루브릭)
    valuation: Optional[CategoryScore] = None         # 밸류에이션 (PER, PBR)
    momentum: Optional[CategoryScore] = None          # 모멘텀 (RSI, MACD, 거래대금)
    sector: Optional[CategoryScore] = None            # 섹터 (섹터순위, 섹터모멘텀)
    shareholder: Optional[CategoryScore] = None       # 주주환원 (배당수익률)

    # 최종 결과
    total_score: float = 0.0  # 0-100 합계
    grade: str = "Hold"       # Strong Buy, Buy, Hold, Sell, Strong Sell

    # 버전 정보
    rubric_version: str = "v2"  # v1: 4개 카테고리, v2: 6개 카테고리, v3: 8개 카테고리


# =============================================================================
# 점수 계산 함수들 - 기술적 분석 (30점)
# =============================================================================


def calc_trend_score(ma20: Optional[float], ma60: Optional[float]) -> float:
    """
    추세 점수 계산 (10점 만점)

    MA20과 MA60의 차이를 기반으로 추세를 판단합니다.

    Args:
        ma20: 20일 이동평균
        ma60: 60일 이동평균

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if ma20 is None or ma60 is None:
        return 5.0  # 데이터 없으면 중간값

    if ma60 == 0:
        return 5.0

    diff_pct = (ma20 - ma60) / ma60 * 100

    if diff_pct >= 5:
        return 10.0  # 강한 상승 추세
    elif diff_pct >= 2:
        return 8.0   # 상승 추세
    elif diff_pct >= 0:
        return 6.0   # 약한 상승/횡보
    elif diff_pct >= -2:
        return 4.0   # 약한 하락
    elif diff_pct >= -5:
        return 2.0   # 하락 추세
    else:
        return 0.0   # 강한 하락 추세


def calc_rsi_score(rsi: Optional[float]) -> float:
    """
    RSI 점수 계산 (10점 만점) - 모멘텀 기반

    상승 추세(RSI 50-70)를 긍정적으로 평가합니다.
    강한 모멘텀(RSI 70+)도 상승 추세의 일부로 인정합니다.

    Args:
        rsi: RSI 값 (0-100)

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if rsi is None:
        return 5.0  # 데이터 없으면 중간값

    # RSI 범위 클램핑
    rsi = max(0, min(100, rsi))

    if 50 <= rsi <= 70:
        return 10.0  # 최적 구간 (건강한 상승 추세)
    elif 70 < rsi <= 80:
        return 8.0   # 강한 모멘텀 (상승 추세 지속)
    elif 40 <= rsi < 50:
        return 7.0   # 중립~상승 전환 기대
    elif rsi > 80:
        return 6.0   # 과열이지만 강세 지속 가능
    elif 30 <= rsi < 40:
        return 4.0   # 약세 구간
    elif 20 <= rsi < 30:
        return 2.0   # 하락 추세
    else:
        return 1.0   # 극단적 약세 (20 미만)


def calc_support_resistance_score(
    current_price: Optional[float],
    low_52w: Optional[float],
    high_52w: Optional[float]
) -> float:
    """
    지지/저항 점수 계산 (10점 만점) - 모멘텀 기반

    현재가가 52주 범위에서 어디에 위치하는지 평가합니다.
    52주 신고가 근처는 강한 상승 추세로 긍정적으로 평가합니다.

    Args:
        current_price: 현재가
        low_52w: 52주 최저가
        high_52w: 52주 최고가

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if None in (current_price, low_52w, high_52w):
        return 5.0  # 데이터 없으면 중간값

    if high_52w == low_52w:
        return 5.0  # 고가 = 저가인 경우

    # 현재가가 52주 범위에서 어디에 위치하는지 (0: 최저, 1: 최고)
    position = (current_price - low_52w) / (high_52w - low_52w)

    if position >= 0.9:
        return 10.0  # 52주 신고가 근처 (강한 상승 추세)
    elif position >= 0.7:
        return 8.0   # 고점 근처 (상승 추세)
    elif position >= 0.5:
        return 6.0   # 중간 (중립)
    elif position >= 0.3:
        return 4.0   # 저점 근처 (약세)
    else:
        return 2.0   # 바닥권 (하락 추세)


# =============================================================================
# 점수 계산 함수들 - 수급 분석 (25점)
# =============================================================================


def calc_foreign_score(foreign_net_buy: Optional[List[float]]) -> float:
    """
    외국인 순매수 점수 계산 (10점 만점)

    최근 5일간 외국인 수급 데이터를 종합적으로 평가합니다.
    - 순매수 일수 (가중치 60%)
    - 누적 순매수 금액 부호 (가중치 40%)

    Args:
        foreign_net_buy: 최근 5일 외국인 순매수 데이터 (억원)

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if not foreign_net_buy:
        return 5.0  # 데이터 없으면 중간값

    # 순매수 일수 계산 (연속이 아닌 전체)
    buy_days = sum(1 for amount in foreign_net_buy if amount > 0)
    total_days = len(foreign_net_buy)

    # 누적 순매수 금액
    total_amount = sum(foreign_net_buy)

    # 순매수 일수 점수 (0-6점): 3일 이상 순매수면 좋음
    if buy_days >= 4:
        days_score = 6.0
    elif buy_days >= 3:
        days_score = 5.0
    elif buy_days >= 2:
        days_score = 3.0
    elif buy_days >= 1:
        days_score = 2.0
    else:
        days_score = 0.0

    # 누적 금액 점수 (0-4점): 전체적으로 순매수인지 순매도인지
    if total_amount > 0:
        amount_score = 4.0  # 누적 순매수
    elif total_amount == 0:
        amount_score = 2.0  # 중립
    else:
        amount_score = 0.0  # 누적 순매도

    return days_score + amount_score


def calc_institution_score(institution_net_buy: Optional[List[float]]) -> float:
    """
    기관 순매수 점수 계산 (10점 만점)

    최근 5일간 기관 수급 데이터를 종합적으로 평가합니다.
    - 순매수 일수 (가중치 60%)
    - 누적 순매수 금액 부호 (가중치 40%)

    Args:
        institution_net_buy: 최근 5일 기관 순매수 데이터 (억원)

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if not institution_net_buy:
        return 5.0  # 데이터 없으면 중간값

    # 순매수 일수 계산 (연속이 아닌 전체)
    buy_days = sum(1 for amount in institution_net_buy if amount > 0)
    total_days = len(institution_net_buy)

    # 누적 순매수 금액
    total_amount = sum(institution_net_buy)

    # 순매수 일수 점수 (0-6점): 3일 이상 순매수면 좋음
    if buy_days >= 4:
        days_score = 6.0
    elif buy_days >= 3:
        days_score = 5.0
    elif buy_days >= 2:
        days_score = 3.0
    elif buy_days >= 1:
        days_score = 2.0
    else:
        days_score = 0.0

    # 누적 금액 점수 (0-4점): 전체적으로 순매수인지 순매도인지
    if total_amount > 0:
        amount_score = 4.0  # 누적 순매수
    elif total_amount == 0:
        amount_score = 2.0  # 중립
    else:
        amount_score = 0.0  # 누적 순매도

    return days_score + amount_score


def calc_trading_value_score(
    trading_value: Optional[float],
    avg_trading_value: Optional[float]
) -> float:
    """
    거래대금 점수 계산 (5점 만점)

    현재 거래대금과 평균 거래대금을 비교합니다.

    Args:
        trading_value: 당일 거래대금 (억원)
        avg_trading_value: 평균 거래대금 (억원)

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if None in (trading_value, avg_trading_value) or avg_trading_value == 0:
        return 2.5  # 데이터 없으면 중간값

    ratio = trading_value / avg_trading_value

    if ratio >= 2.0:
        return 5.0   # 거래 폭증
    elif ratio >= 1.5:
        return 4.0   # 거래 증가
    elif ratio >= 1.0:
        return 3.0   # 평균 수준
    elif ratio >= 0.5:
        return 2.0   # 거래 감소
    else:
        return 1.0   # 거래 급감


# =============================================================================
# 점수 계산 함수들 - 펀더멘털 분석 (25점)
# =============================================================================


def calc_per_score(per: Optional[float], sector_avg_per: Optional[float]) -> float:
    """
    PER 점수 계산 (10점 만점)

    업종 평균 PER 대비 현재 PER을 비교합니다.

    Args:
        per: 현재 PER
        sector_avg_per: 업종 평균 PER

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if per is None:
        return 5.0  # 데이터 없음
    if per < 0:
        return 0.0  # 적자 기업
    if sector_avg_per is None or sector_avg_per <= 0:
        sector_avg_per = 15.0  # 기본값

    ratio = per / sector_avg_per

    if ratio <= 0.5:
        return 10.0  # 매우 저평가
    elif ratio <= 0.7:
        return 8.0   # 저평가
    elif ratio <= 1.0:
        return 6.0   # 적정~약간 저평가
    elif ratio <= 1.3:
        return 4.0   # 약간 고평가
    elif ratio <= 1.5:
        return 2.0   # 고평가
    else:
        return 0.0   # 매우 고평가


def calc_growth_score(op_growth: Optional[float]) -> float:
    """
    영업이익 성장률 점수 계산 (10점 만점)

    성장률에 따라 더 세분화된 점수를 부여합니다.
    - 100% 이상: 폭발적 성장
    - 50% 이상: 고성장
    - 20% 이상: 양호한 성장

    Args:
        op_growth: 영업이익 성장률 (YoY, %)

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if op_growth is None:
        return 5.0  # 데이터 없으면 중간값

    if op_growth >= 100:
        return 10.0  # 폭발적 성장 (100% 이상)
    elif op_growth >= 50:
        return 9.0   # 매우 높은 성장
    elif op_growth >= 30:
        return 8.0   # 고성장
    elif op_growth >= 20:
        return 7.0   # 양호한 성장
    elif op_growth >= 10:
        return 6.0   # 완만한 성장
    elif op_growth >= 0:
        return 4.0   # 정체
    elif op_growth >= -10:
        return 2.0   # 역성장
    elif op_growth >= -30:
        return 1.0   # 큰 역성장
    else:
        return 0.0   # 급격한 역성장


def calc_debt_score(debt_ratio: Optional[float]) -> float:
    """
    부채비율 점수 계산 (5점 만점)

    Args:
        debt_ratio: 부채비율 (%)

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if debt_ratio is None:
        return 2.5  # 데이터 없으면 중간값

    if debt_ratio <= 50:
        return 5.0   # 매우 건전
    elif debt_ratio <= 100:
        return 4.0   # 건전
    elif debt_ratio <= 150:
        return 3.0   # 보통
    elif debt_ratio <= 200:
        return 2.0   # 주의
    else:
        return 1.0   # 위험


# =============================================================================
# 점수 계산 함수들 - 시장 환경 (20점)
# =============================================================================


def calc_news_score(avg_sentiment: Optional[float]) -> float:
    """
    뉴스 센티먼트 점수 계산 (10점 만점)

    Args:
        avg_sentiment: 센티먼트 평균 (-1.0 ~ 1.0)

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if avg_sentiment is None:
        return 5.0  # 뉴스 없으면 중립

    # -1.0~1.0을 0~10점으로 변환
    # -1.0 -> 0.0, 0.0 -> 5.0, 1.0 -> 10.0
    score = (avg_sentiment + 1.0) * 5.0
    return max(0.0, min(10.0, score))


def calc_sector_momentum_score(sector_return_5d: Optional[float]) -> float:
    """
    섹터 모멘텀 점수 계산 (5점 만점)

    Args:
        sector_return_5d: 섹터 5일 수익률 (%)

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if sector_return_5d is None:
        return 2.5  # 데이터 없으면 중간값

    if sector_return_5d >= 5:
        return 5.0
    elif sector_return_5d >= 2:
        return 4.0
    elif sector_return_5d >= 0:
        return 3.0
    elif sector_return_5d >= -2:
        return 2.0
    else:
        return 1.0


def calc_analyst_score(
    target_price: Optional[float],
    current_price: Optional[float]
) -> float:
    """
    애널리스트 전망 점수 계산 (5점 만점)

    목표가 대비 현재가의 상승 여력을 평가합니다.

    Args:
        target_price: 애널리스트 목표가
        current_price: 현재가

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if None in (target_price, current_price) or current_price == 0:
        return 2.5  # 데이터 없으면 중간값

    upside = (target_price - current_price) / current_price * 100

    if upside >= 30:
        return 5.0   # 상승 여력 큼
    elif upside >= 15:
        return 4.0   # 상승 여력 있음
    elif upside >= 0:
        return 3.0   # 적정가 근처
    elif upside >= -15:
        return 2.0   # 약간 고평가
    else:
        return 1.0   # 고평가


# =============================================================================
# 투자 등급 판정
# =============================================================================


def get_investment_grade(score: float) -> str:
    """
    총점을 기반으로 투자 등급을 반환합니다.

    Args:
        score: 총점 (0-100)

    Returns:
        투자 등급 문자열
    """
    return get_grade_from_score(int(score))


# =============================================================================
# RubricEngine
# =============================================================================


class RubricEngine:
    """
    루브릭 평가 엔진

    MarketData, FundamentalData, NewsData를 입력받아
    종합 투자 점수를 산출합니다.

    사용 예시:
        engine = RubricEngine()

        # 데이터 준비
        market_data = MarketData(...)
        fundamental_data = FundamentalData(...)
        news_data = NewsData(...)

        # 평가 실행
        result = engine.calculate(
            symbol="005930",
            name="삼성전자",
            market_data=market_data,
            fundamental_data=fundamental_data,
            news_data=news_data
        )

        print(f"총점: {result.total_score}, 등급: {result.grade}")

        # V3 (8대 핵심 루브릭) 사용
        engine_v3 = RubricEngine(use_v3=True)
        result_v3 = engine_v3.calculate(...)
    """

    def __init__(self, use_v2: bool = True, use_v3: bool = False):
        """
        루브릭 엔진 초기화

        Args:
            use_v2: True면 V2 (6개 카테고리), False면 V1 (4개 카테고리)
            use_v3: True면 V3 (8대 핵심 루브릭, use_v2보다 우선)
        """
        self.use_v3 = use_v3
        self.use_v2 = use_v2 if not use_v3 else False
        if use_v3:
            self.weights = RUBRIC_WEIGHTS_V3
        elif use_v2:
            self.weights = RUBRIC_WEIGHTS
        else:
            self.weights = RUBRIC_WEIGHTS_V1

    def calculate(
        self,
        symbol: str,
        name: str,
        market_data: Optional[Any] = None,
        fundamental_data: Optional[Any] = None,
        news_data: Optional[Any] = None,
        low_52w: Optional[float] = None,
        high_52w: Optional[float] = None,
        sector_return_5d: Optional[float] = None,
        target_price: Optional[float] = None,
        # V2 추가 파라미터 (리스크 평가)
        atr_pct: Optional[float] = None,
        beta: Optional[float] = None,
        max_drawdown_pct: Optional[float] = None,
        # V2 추가 파라미터 (상대 강도)
        sector_rank: Optional[int] = None,
        sector_total: Optional[int] = None,
        stock_return_20d: Optional[float] = None,
        market_return_20d: Optional[float] = None,
        # V3 추가 파라미터 (주주환원)
        dividend_yield: Optional[float] = None,
    ) -> RubricResult:
        """
        루브릭 평가를 수행합니다.

        Args:
            symbol: 종목 코드
            name: 종목명
            market_data: MarketData 객체 (기술적 지표, 수급 데이터)
            fundamental_data: FundamentalData 객체 (재무제표)
            news_data: NewsData 객체 (뉴스 센티먼트)
            low_52w: 52주 최저가 (선택)
            high_52w: 52주 최고가 (선택)
            sector_return_5d: 섹터 5일 수익률 (선택)
            target_price: 애널리스트 목표가 (선택)
            atr_pct: ATR 퍼센트 (V2, 선택)
            beta: 베타 값 (V2, 선택)
            max_drawdown_pct: 최대 낙폭 (V2, 선택)
            sector_rank: 섹터 내 순위 (V2, 선택)
            sector_total: 섹터 내 전체 종목 수 (V2, 선택)
            stock_return_20d: 종목 20일 수익률 (V2, 선택)
            market_return_20d: 시장 20일 수익률 (V2, 선택)
            dividend_yield: 배당수익률 (V3, 선택)

        Returns:
            RubricResult 객체
        """
        # V3 모드: 8대 핵심 루브릭
        if self.use_v3:
            return self._calculate_v3(
                symbol=symbol,
                name=name,
                market_data=market_data,
                fundamental_data=fundamental_data,
                news_data=news_data,
                low_52w=low_52w,
                high_52w=high_52w,
                sector_return_5d=sector_return_5d,
                target_price=target_price,
                atr_pct=atr_pct,
                beta=beta,
                max_drawdown_pct=max_drawdown_pct,
                sector_rank=sector_rank,
                sector_total=sector_total,
                stock_return_20d=stock_return_20d,
                market_return_20d=market_return_20d,
                dividend_yield=dividend_yield,
            )

        # V1/V2 모드: 기존 로직
        # 1. 기술적 분석 점수 계산 (V2: 25점, V1: 30점)
        technical = self._calculate_technical(market_data, low_52w, high_52w)

        # 2. 수급 분석 점수 계산 (V2: 20점, V1: 25점)
        supply = self._calculate_supply(market_data)

        # 3. 펀더멘털 분석 점수 계산 (V2: 20점, V1: 25점)
        fundamental = self._calculate_fundamental(fundamental_data)

        # 4. 시장 환경 점수 계산 (V2: 15점, V1: 20점)
        market = self._calculate_market(
            news_data, market_data, sector_return_5d, target_price
        )

        # V2 카테고리
        risk = None
        relative_strength = None

        if self.use_v2:
            # 5. 리스크 평가 (10점)
            risk = self._calculate_risk(atr_pct, beta, max_drawdown_pct)

            # 6. 상대 강도 (10점)
            relative_strength = self._calculate_relative_strength(
                sector_rank, sector_total, stock_return_20d, market_return_20d
            )

        # 총점 계산
        total_score = (
            technical.weighted_score +
            supply.weighted_score +
            fundamental.weighted_score +
            market.weighted_score
        )

        if self.use_v2 and risk and relative_strength:
            total_score += risk.weighted_score + relative_strength.weighted_score

        # 투자 등급 판정
        grade = get_investment_grade(total_score)

        return RubricResult(
            symbol=symbol,
            name=name,
            technical=technical,
            supply=supply,
            fundamental=fundamental,
            market=market,
            risk=risk,
            relative_strength=relative_strength,
            total_score=round(total_score, 1),
            grade=grade,
            rubric_version="v2" if self.use_v2 else "v1",
        )

    def _calculate_technical(
        self,
        market_data: Optional[Any],
        low_52w: Optional[float],
        high_52w: Optional[float]
    ) -> CategoryScore:
        """
        기술적 분석 점수 계산

        V2 (25점): 추세(6) + RSI(6) + 지지/저항(6) + MACD(4) + ADX(3)
        V1 (30점): 추세(10) + RSI(10) + 지지/저항(10)
        """
        weight = self.weights["technical"]

        # 데이터 추출
        ma20 = getattr(market_data, "ma20", None) if market_data else None
        ma60 = getattr(market_data, "ma60", None) if market_data else None
        rsi = getattr(market_data, "rsi", None) if market_data else None
        current_price = getattr(market_data, "current_price", None) if market_data else None

        # V2 추가 지표
        macd = getattr(market_data, "macd", None) if market_data else None
        macd_signal = getattr(market_data, "macd_signal", None) if market_data else None
        adx = getattr(market_data, "adx", None) if market_data else None

        # 52주 위치 계산
        position_52w = None
        if None not in (current_price, low_52w, high_52w) and high_52w != low_52w:
            position_52w = (current_price - low_52w) / (high_52w - low_52w) * 100  # 퍼센트

        if self.use_v2:
            # V2: 5개 지표 (6+6+6+4+3 = 25점 기준 환산)
            # 개별 점수를 비율로 환산 (만점 25점 기준)
            trend_raw = calc_trend_score(ma20, ma60)  # 0-10
            rsi_raw = calc_rsi_score(rsi)  # 0-10
            sr_raw = calc_support_resistance_score(current_price, low_52w, high_52w)  # 0-10
            macd_raw = calc_macd_score(macd, macd_signal)  # 0-5
            adx_raw = calc_adx_score(adx)  # 0-5

            # 비율 환산 (각 지표의 최대값에서의 비율로 계산)
            trend_score = (trend_raw / 10) * 6  # 0-6
            rsi_score_val = (rsi_raw / 10) * 6  # 0-6
            sr_score = (sr_raw / 10) * 6  # 0-6
            macd_score_val = (macd_raw / 5) * 4  # 0-4
            adx_score_val = (adx_raw / 5) * 3  # 0-3

            raw_total = trend_score + rsi_score_val + sr_score + macd_score_val + adx_score_val  # 0-25
            normalized_score = (raw_total / 25) * 100

            details = {
                "trend": round(trend_score, 2),
                "rsi": round(rsi_score_val, 2),
                "support_resistance": round(sr_score, 2),
                "macd": round(macd_score_val, 2),
                "adx": round(adx_score_val, 2),
                # 원본 지표 값 추가
                "ma20_value": round(ma20, 0) if ma20 else None,
                "ma60_value": round(ma60, 0) if ma60 else None,
                "rsi_value": round(rsi, 1) if rsi else None,
                "macd_value": round(macd, 2) if macd else None,
                "macd_signal_value": round(macd_signal, 2) if macd_signal else None,
                "adx_value": round(adx, 1) if adx else None,
                "current_price": round(current_price, 0) if current_price else None,
                "low_52w": round(low_52w, 0) if low_52w else None,
                "high_52w": round(high_52w, 0) if high_52w else None,
                "position_52w": round(position_52w, 1) if position_52w else None,
            }
        else:
            # V1: 3개 지표 (10+10+10 = 30점)
            trend_score = calc_trend_score(ma20, ma60)  # 0-10
            rsi_score_val = calc_rsi_score(rsi)  # 0-10
            sr_score = calc_support_resistance_score(current_price, low_52w, high_52w)  # 0-10

            raw_total = trend_score + rsi_score_val + sr_score  # 0-30
            normalized_score = (raw_total / 30) * 100

            details = {
                "trend": trend_score,
                "rsi": rsi_score_val,
                "support_resistance": sr_score,
                # 원본 지표 값 추가
                "ma20_value": round(ma20, 0) if ma20 else None,
                "ma60_value": round(ma60, 0) if ma60 else None,
                "rsi_value": round(rsi, 1) if rsi else None,
                "current_price": round(current_price, 0) if current_price else None,
                "low_52w": round(low_52w, 0) if low_52w else None,
                "high_52w": round(high_52w, 0) if high_52w else None,
                "position_52w": round(position_52w, 1) if position_52w else None,
            }

        # 가중치 적용 점수
        weighted_score = (normalized_score / 100) * weight

        return CategoryScore(
            name="technical",
            score=round(normalized_score, 1),
            max_score=weight,
            weighted_score=round(weighted_score, 1),
            details=details
        )

    def _calculate_supply(self, market_data: Optional[Any]) -> CategoryScore:
        """수급 분석 점수 계산 (25점 만점)"""
        weight = self.weights["supply"]  # 25

        # 데이터 추출
        foreign_net = getattr(market_data, "foreign_net_buy", None) if market_data else None
        inst_net = getattr(market_data, "institution_net_buy", None) if market_data else None
        trading_value = getattr(market_data, "trading_value", None) if market_data else None

        # 평균 거래대금 계산 (volume * price / 억원)
        # MarketData에는 avg_trading_value가 없으므로 trading_value만 사용
        # 비교 기준이 없으면 중간값 사용
        avg_trading_value = None

        # 세부 점수 계산
        foreign_score = calc_foreign_score(foreign_net)  # 0-10
        inst_score = calc_institution_score(inst_net)  # 0-10
        tv_score = calc_trading_value_score(trading_value, avg_trading_value)  # 0-5

        # 정규화된 점수 (0-100)
        raw_total = foreign_score + inst_score + tv_score  # 0-25
        normalized_score = (raw_total / 25) * 100

        # 가중치 적용 점수
        weighted_score = (normalized_score / 100) * weight

        # 외국인/기관 연속 순매수 일수 계산
        foreign_consecutive = 0
        if foreign_net:
            for amount in foreign_net:
                if amount > 0:
                    foreign_consecutive += 1
                else:
                    break

        inst_consecutive = 0
        if inst_net:
            for amount in inst_net:
                if amount > 0:
                    inst_consecutive += 1
                else:
                    break

        return CategoryScore(
            name="supply",
            score=round(normalized_score, 1),
            max_score=weight,
            weighted_score=round(weighted_score, 1),
            details={
                "foreign": foreign_score,
                "institution": inst_score,
                "trading_value": tv_score,
                # 원본 지표 값 추가
                "foreign_net_5d": foreign_net if foreign_net else [],
                "foreign_consecutive_days": foreign_consecutive,
                "institution_net_5d": inst_net if inst_net else [],
                "institution_consecutive_days": inst_consecutive,
                "trading_value_amount": round(trading_value, 2) if trading_value else None,
            }
        )

    def _calculate_fundamental(self, fundamental_data: Optional[Any]) -> CategoryScore:
        """
        펀더멘털 분석 점수 계산

        V2 (20점): PER(4) + PBR(4) + ROE(4) + 성장률(5) + 부채비율(3)
        V1 (25점): PER(10) + 성장률(10) + 부채비율(5)
        """
        weight = self.weights["fundamental"]

        # 데이터 추출
        per = getattr(fundamental_data, "per", None) if fundamental_data else None
        sector_avg_per = getattr(fundamental_data, "sector_avg_per", None) if fundamental_data else None
        op_growth = getattr(fundamental_data, "operating_profit_growth", None) if fundamental_data else None
        debt_ratio = getattr(fundamental_data, "debt_ratio", None) if fundamental_data else None

        # V2 추가 지표
        pbr = getattr(fundamental_data, "pbr", None) if fundamental_data else None
        sector_avg_pbr = getattr(fundamental_data, "sector_avg_pbr", None) if fundamental_data else None
        roe = getattr(fundamental_data, "roe", None) if fundamental_data else None

        if self.use_v2:
            # V2: 5개 지표 (4+4+4+5+3 = 20점 기준)
            per_raw = calc_per_score(per, sector_avg_per)  # 0-10
            pbr_raw = calc_pbr_score(pbr, sector_avg_pbr)  # 0-5
            roe_raw = calc_roe_score(roe)  # 0-5
            growth_raw = calc_growth_score(op_growth)  # 0-10
            debt_raw = calc_debt_score(debt_ratio)  # 0-5

            # 비율 환산
            per_score_val = (per_raw / 10) * 4  # 0-4
            pbr_score_val = (pbr_raw / 5) * 4  # 0-4
            roe_score_val = (roe_raw / 5) * 4  # 0-4
            growth_score_val = (growth_raw / 10) * 5  # 0-5
            debt_score_val = (debt_raw / 5) * 3  # 0-3

            raw_total = per_score_val + pbr_score_val + roe_score_val + growth_score_val + debt_score_val  # 0-20
            normalized_score = (raw_total / 20) * 100

            details = {
                "per": round(per_score_val, 2),
                "pbr": round(pbr_score_val, 2),
                "roe": round(roe_score_val, 2),
                "growth": round(growth_score_val, 2),
                "debt": round(debt_score_val, 2),
                # 원본 지표 값 추가
                "per_value": round(per, 2) if per else None,
                "pbr_value": round(pbr, 2) if pbr else None,
                "roe_value": round(roe, 2) if roe else None,
                "sector_avg_per": round(sector_avg_per, 2) if sector_avg_per else None,
                "sector_avg_pbr": round(sector_avg_pbr, 2) if sector_avg_pbr else None,
                "op_growth_value": round(op_growth, 2) if op_growth else None,
                "debt_ratio_value": round(debt_ratio, 2) if debt_ratio else None,
            }
        else:
            # V1: 3개 지표 (10+10+5 = 25점)
            per_score_val = calc_per_score(per, sector_avg_per)  # 0-10
            growth_score_val = calc_growth_score(op_growth)  # 0-10
            debt_score_val = calc_debt_score(debt_ratio)  # 0-5

            raw_total = per_score_val + growth_score_val + debt_score_val  # 0-25
            normalized_score = (raw_total / 25) * 100

            details = {
                "per": per_score_val,
                "growth": growth_score_val,
                "debt": debt_score_val,
                # 원본 지표 값 추가
                "per_value": round(per, 2) if per else None,
                "sector_avg_per": round(sector_avg_per, 2) if sector_avg_per else None,
                "op_growth_value": round(op_growth, 2) if op_growth else None,
                "debt_ratio_value": round(debt_ratio, 2) if debt_ratio else None,
            }

        # 가중치 적용 점수
        weighted_score = (normalized_score / 100) * weight

        return CategoryScore(
            name="fundamental",
            score=round(normalized_score, 1),
            max_score=weight,
            weighted_score=round(weighted_score, 1),
            details=details
        )

    def _calculate_market(
        self,
        news_data: Optional[Any],
        market_data: Optional[Any],
        sector_return_5d: Optional[float],
        target_price: Optional[float]
    ) -> CategoryScore:
        """시장 환경 점수 계산 (20점 만점)"""
        weight = self.weights["market"]  # 20

        # 데이터 추출
        avg_sentiment = getattr(news_data, "avg_sentiment_score", None) if news_data else None
        current_price = getattr(market_data, "current_price", None) if market_data else None

        # 세부 점수 계산
        news_score = calc_news_score(avg_sentiment)  # 0-10
        sector_score = calc_sector_momentum_score(sector_return_5d)  # 0-5
        analyst_score = calc_analyst_score(target_price, current_price)  # 0-5

        # 정규화된 점수 (0-100)
        raw_total = news_score + sector_score + analyst_score  # 0-20
        normalized_score = (raw_total / 20) * 100

        # 가중치 적용 점수
        weighted_score = (normalized_score / 100) * weight

        return CategoryScore(
            name="market",
            score=round(normalized_score, 1),
            max_score=weight,
            weighted_score=round(weighted_score, 1),
            details={
                "news": news_score,
                "sector_momentum": sector_score,
                "analyst": analyst_score,
            }
        )

    def _calculate_risk(
        self,
        atr_pct: Optional[float],
        beta: Optional[float],
        max_drawdown_pct: Optional[float]
    ) -> CategoryScore:
        """
        리스크 평가 점수 계산 (10점 만점)

        변동성(4점) + 베타(3점) + 하방리스크(3점)
        """
        weight = self.weights.get("risk", 10)

        # 세부 점수 계산
        volatility_score = calc_volatility_score(atr_pct)  # 0-4
        beta_score = calc_beta_score(beta)  # 0-3
        downside_score = calc_downside_risk_score(max_drawdown_pct)  # 0-3

        # 정규화된 점수 (0-100)
        raw_total = volatility_score + beta_score + downside_score  # 0-10
        normalized_score = (raw_total / 10) * 100

        # 가중치 적용 점수
        weighted_score = (normalized_score / 100) * weight

        return CategoryScore(
            name="risk",
            score=round(normalized_score, 1),
            max_score=weight,
            weighted_score=round(weighted_score, 1),
            details={
                "volatility": volatility_score,
                "beta": beta_score,
                "downside_risk": downside_score,
                # 원본 지표 값 추가
                "atr_pct_value": round(atr_pct, 2) if atr_pct else None,
                "beta_value": round(beta, 2) if beta else None,
                "max_drawdown_value": round(max_drawdown_pct, 2) if max_drawdown_pct else None,
            }
        )

    def _calculate_relative_strength(
        self,
        sector_rank: Optional[int],
        sector_total: Optional[int],
        stock_return: Optional[float],
        market_return: Optional[float]
    ) -> CategoryScore:
        """
        상대 강도 점수 계산 (10점 만점)

        섹터내순위(5점) + 시장대비알파(5점)
        """
        weight = self.weights.get("relative_strength", 10)

        # 세부 점수 계산
        rank_score = calc_sector_rank_score(sector_rank, sector_total)  # 0-5
        alpha_score = calc_alpha_score(stock_return, market_return)  # 0-5

        # 정규화된 점수 (0-100)
        raw_total = rank_score + alpha_score  # 0-10
        normalized_score = (raw_total / 10) * 100

        # 가중치 적용 점수
        weighted_score = (normalized_score / 100) * weight

        # 알파 계산
        alpha = None
        if stock_return is not None and market_return is not None:
            alpha = stock_return - market_return

        return CategoryScore(
            name="relative_strength",
            score=round(normalized_score, 1),
            max_score=weight,
            weighted_score=round(weighted_score, 1),
            details={
                "sector_rank": rank_score,
                "alpha": alpha_score,
                # 원본 지표 값 추가
                "sector_rank_value": sector_rank,
                "sector_total_value": sector_total,
                "stock_return_value": round(stock_return, 2) if stock_return else None,
                "market_return_value": round(market_return, 2) if market_return else None,
                "alpha_value": round(alpha, 2) if alpha else None,
            }
        )

    def calculate_with_all_missing_data(self, symbol: str, name: str) -> RubricResult:
        """
        모든 데이터가 없는 경우의 평가 (중간값 반환)

        Args:
            symbol: 종목 코드
            name: 종목명

        Returns:
            모든 항목이 중간값인 RubricResult
        """
        return self.calculate(symbol=symbol, name=name)

    def _calculate_v3(
        self,
        symbol: str,
        name: str,
        market_data: Optional[Any],
        fundamental_data: Optional[Any],
        news_data: Optional[Any],
        low_52w: Optional[float],
        high_52w: Optional[float],
        sector_return_5d: Optional[float],
        target_price: Optional[float],
        atr_pct: Optional[float],
        beta: Optional[float],
        max_drawdown_pct: Optional[float],
        sector_rank: Optional[int],
        sector_total: Optional[int],
        stock_return_20d: Optional[float],
        market_return_20d: Optional[float],
        dividend_yield: Optional[float],
    ) -> RubricResult:
        """
        V3 8대 핵심 루브릭 평가를 수행합니다. (결측치 정형화 및 거래대금 20일 평균 연동 탑재)
        """
        # 데이터 추출 - 기술적/모멘텀
        ma20 = getattr(market_data, "ma20", None) if market_data else None
        ma60 = getattr(market_data, "ma60", None) if market_data else None
        rsi = getattr(market_data, "rsi", None) if market_data else None
        current_price = getattr(market_data, "current_price", None) if market_data else None
        macd = getattr(market_data, "macd", None) if market_data else None
        macd_signal = getattr(market_data, "macd_signal", None) if market_data else None
        adx = getattr(market_data, "adx", None) if market_data else None
        trading_value = getattr(market_data, "trading_value", None) if market_data else None
        avg_trading_value_20d = getattr(market_data, "avg_trading_value_20d", None) if market_data else None

        # 데이터 추출 - 수급
        foreign_net = getattr(market_data, "foreign_net_buy", None) if market_data else None
        inst_net = getattr(market_data, "institution_net_buy", None) if market_data else None

        # 데이터 추출 - 펀더멘털
        per = getattr(fundamental_data, "per", None) if fundamental_data else None
        sector_avg_per = getattr(fundamental_data, "sector_avg_per", None) if fundamental_data else None
        pbr = getattr(fundamental_data, "pbr", None) if fundamental_data else None
        sector_avg_pbr = getattr(fundamental_data, "sector_avg_pbr", None) if fundamental_data else None
        roe = getattr(fundamental_data, "roe", None) if fundamental_data else None
        op_growth = getattr(fundamental_data, "operating_profit_growth", None) if fundamental_data else None
        debt_ratio = getattr(fundamental_data, "debt_ratio", None) if fundamental_data else None

        # 데이터 추출 - 뉴스
        avg_sentiment = getattr(news_data, "avg_sentiment_score", None) if news_data else None

        # 52주 위치 계산
        position_52w = None
        if None not in (current_price, low_52w, high_52w) and high_52w != low_52w:
            position_52w = (current_price - low_52w) / (high_52w - low_52w) * 100

        # =================================================================
        # 1. 밸류에이션 (20점): PEG(10) + Valuation Band(10)
        # =================================================================
        val_raw_total = 0.0
        val_max_possible = 0.0
        peg_missing = (per is None) or (op_growth is None)
        band_missing = (current_price is None) or (low_52w is None) or (high_52w is None)

        if not peg_missing:
            peg_score, peg_val = calc_peg_ratio(per, op_growth)
            val_raw_total += peg_score
            val_max_possible += 10.0
        else:
            peg_score = 0.0
            peg_val = 99.0

        if not band_missing:
            band_score = calc_valuation_band_score(current_price, low_52w, high_52w)
            val_raw_total += band_score
            val_max_possible += 10.0
        else:
            band_score = 0.0

        if val_max_possible > 0:
            valuation_normalized = (val_raw_total / val_max_possible) * 100
            valuation_weighted = (valuation_normalized / 100) * self.weights["valuation"]
            valuation_has_data = True
        else:
            valuation_normalized = 50.0
            valuation_weighted = 0.0
            valuation_has_data = False

        valuation = CategoryScore(
            name="valuation",
            score=round(valuation_normalized, 1),
            max_score=self.weights["valuation"],
            weighted_score=round((valuation_normalized / 100) * self.weights["valuation"], 1),
            details={
                "peg_score": round(peg_score, 2),
                "band_score": round(band_score, 2),
                "peg_value": round(peg_val, 2) if peg_val != 99.0 else None,
                "per_value": round(per, 2) if per else None,
                "pbr_value": round(pbr, 2) if pbr else None,
                "sector_avg_per": round(sector_avg_per, 2) if sector_avg_per else None,
                "sector_avg_pbr": round(sector_avg_pbr, 2) if sector_avg_pbr else None,
                "current_price": current_price,
                "low_52w": low_52w,
                "high_52w": high_52w,
            }
        )

        # =================================================================
        # 2. 펀더멘털 (15점): ROE(3) + F-Score(9) + 부채비율(3)
        # =================================================================
        roe_raw = calc_roe_score(roe)  # 0-5
        growth_raw = calc_growth_score(op_growth)  # 0-10
        debt_raw = calc_debt_score(debt_ratio)  # 0-5
        
        # 다개년 시계열 맵 추출
        yearly_history = getattr(fundamental_data, "yearly_history", {})
        f_score = calc_piotroski_f_score(yearly_history)  # 0-9

        # Piotroski F-score 결측 여부 체크
        # 만약 F-Score가 0점이어도 yearly_history가 정상 존재하면 결측이 아닌 0점 득점으로 인정
        f_score_missing = not yearly_history

        fund_raw_total = 0.0
        fund_max_possible = 0.0

        roe_missing = roe is None
        debt_missing = debt_ratio is None

        # F-Score 정상 산출 여부에 따른 유연한 결측치 폴백(Fallback) 보장
        if f_score_missing:
            # [폴백 모드]: 다개년 시계열 결측 시 기존의 단년도 영업이익성장률(6점 만점)로 대체 연동
            growth_missing = op_growth is None
            if not growth_missing:
                f_score_scaled = (growth_raw / 10) * 6  # 0-6
                fund_raw_total += f_score_scaled
                fund_max_possible += 6.0
            else:
                f_score_scaled = 0.0
                # growth와 f_score 모두 없으므로 max_possible에 더하지 않음 (결측)
            
            if not roe_missing:
                roe_scaled = roe_raw  # 0-5
                fund_raw_total += roe_scaled
                fund_max_possible += 5.0
            else:
                roe_scaled = 0.0

            if not debt_missing:
                debt_scaled = (debt_raw / 5) * 4  # 0-4
                fund_raw_total += debt_scaled
                fund_max_possible += 4.0
            else:
                debt_scaled = 0.0
        else:
            # [우량 퀀트 모드]: ROE(3점) + F-Score(9점) + 부채비율(3점) = 총 15점 만점 배분
            f_score_scaled = (f_score / 9) * 9  # 0-9
            fund_raw_total += f_score_scaled
            fund_max_possible += 9.0

            if not roe_missing:
                roe_scaled = (roe_raw / 5) * 3  # 0-3
                fund_raw_total += roe_scaled
                fund_max_possible += 3.0
            else:
                roe_scaled = 0.0

            if not debt_missing:
                debt_scaled = (debt_raw / 5) * 3  # 0-3
                fund_raw_total += debt_scaled
                fund_max_possible += 3.0
            else:
                debt_scaled = 0.0

        if fund_max_possible > 0:
            fundamental_normalized = (fund_raw_total / fund_max_possible) * 100
            fundamental_weighted = (fundamental_normalized / 100) * self.weights["fundamental"]
            fundamental_has_data = True
        else:
            fundamental_normalized = 50.0
            fundamental_weighted = 0.0
            fundamental_has_data = False

        fundamental = CategoryScore(
            name="fundamental",
            score=round(fundamental_normalized, 1),
            max_score=self.weights["fundamental"],
            weighted_score=round((fundamental_normalized / 100) * self.weights["fundamental"], 1),
            details={
                "roe": round(roe_scaled, 2),
                "f_score": round(f_score_scaled, 2),
                "debt": round(debt_scaled, 2),
                "roe_value": round(roe, 2) if roe else None,
                "piotroski_f_score_raw": f_score if not f_score_missing else None,
                "op_growth_value": round(op_growth, 2) if op_growth else None,
                "debt_ratio_value": round(debt_ratio, 2) if debt_ratio else None,
            }
        )

        # =================================================================
        # 3. 수급 (15점): 외국인(7.5) + 기관(7.5)
        # =================================================================
        foreign_missing = not foreign_net
        inst_missing = not inst_net

        supply_raw_total = 0.0
        supply_max_possible = 0.0

        if not foreign_missing:
            foreign_raw = calc_foreign_score(foreign_net)  # 0-10
            foreign_scaled = (foreign_raw / 10) * 7.5  # 0-7.5
            supply_raw_total += foreign_scaled
            supply_max_possible += 7.5
        else:
            foreign_scaled = 0.0

        if not inst_missing:
            inst_raw = calc_institution_score(inst_net)  # 0-10
            inst_scaled = (inst_raw / 10) * 7.5  # 0-7.5
            supply_raw_total += inst_scaled
            supply_max_possible += 7.5
        else:
            inst_scaled = 0.0

        if supply_max_possible > 0:
            supply_normalized = (supply_raw_total / supply_max_possible) * 100
            supply_weighted = (supply_normalized / 100) * self.weights["supply"]
            supply_has_data = True
        else:
            supply_normalized = 50.0
            supply_weighted = 0.0
            supply_has_data = False

        # 연속 순매수 일수 계산
        foreign_consecutive = 0
        if foreign_net:
            for amount in foreign_net:
                if amount > 0:
                    foreign_consecutive += 1
                else:
                    break
        inst_consecutive = 0
        if inst_net:
            for amount in inst_net:
                if amount > 0:
                    inst_consecutive += 1
                else:
                    break

        supply = CategoryScore(
            name="supply",
            score=round(supply_normalized, 1),
            max_score=self.weights["supply"],
            weighted_score=round((supply_normalized / 100) * self.weights["supply"], 1),
            details={
                "foreign": round(foreign_scaled, 2),
                "institution": round(inst_scaled, 2),
                "foreign_net_5d": foreign_net if foreign_net else [],
                "foreign_consecutive_days": foreign_consecutive,
                "institution_net_5d": inst_net if inst_net else [],
                "institution_consecutive_days": inst_consecutive,
            }
        )

        # =================================================================
        # 4. 모멘텀 (15점): RSI(5) + MACD(5) + 거래대금(5)
        # =================================================================
        rsi_missing = rsi is None
        macd_missing = macd is None or macd_signal is None
        tv_missing = trading_value is None or avg_trading_value_20d is None

        momentum_raw_total = 0.0
        momentum_max_possible = 0.0

        if not rsi_missing:
            rsi_raw = calc_rsi_score(rsi)  # 0-10
            rsi_scaled = (rsi_raw / 10) * 5  # 0-5
            momentum_raw_total += rsi_scaled
            momentum_max_possible += 5.0
        else:
            rsi_scaled = 0.0

        if not macd_missing:
            macd_raw = calc_macd_score(macd, macd_signal)  # 0-5
            macd_scaled = macd_raw  # 0-5
            momentum_raw_total += macd_scaled
            momentum_max_possible += 5.0
        else:
            macd_scaled = 0.0

        if not tv_missing:
            # avg_trading_value_20d 탑재하여 연동 (H2 해결)
            tv_raw = calc_trading_value_score(trading_value, avg_trading_value_20d)  # 0-5
            tv_scaled = tv_raw  # 0-5
            momentum_raw_total += tv_scaled
            momentum_max_possible += 5.0
        else:
            tv_scaled = 0.0

        if momentum_max_possible > 0:
            momentum_normalized = (momentum_raw_total / momentum_max_possible) * 100
            momentum_weighted = (momentum_normalized / 100) * self.weights["momentum"]
            momentum_has_data = True
        else:
            momentum_normalized = 50.0
            momentum_weighted = 0.0
            momentum_has_data = False

        momentum = CategoryScore(
            name="momentum",
            score=round(momentum_normalized, 1),
            max_score=self.weights["momentum"],
            weighted_score=round((momentum_normalized / 100) * self.weights["momentum"], 1),
            details={
                "rsi": round(rsi_scaled, 2),
                "macd": round(macd_scaled, 2),
                "trading_value": round(tv_scaled, 2),
                "rsi_value": round(rsi, 1) if rsi else None,
                "macd_value": round(macd, 2) if macd else None,
                "macd_signal_value": round(macd_signal, 2) if macd_signal else None,
                "trading_value_amount": round(trading_value, 2) if trading_value else None,
            }
        )

        # =================================================================
        # 5. 기술적 (10점): 추세(4) + 지지/저항(3) + ADX(3)
        # =================================================================
        trend_missing = ma20 is None or ma60 is None
        sr_missing = current_price is None or low_52w is None or high_52w is None
        adx_missing = adx is None

        technical_raw_total = 0.0
        technical_max_possible = 0.0

        if not trend_missing:
            trend_raw = calc_trend_score(ma20, ma60)  # 0-10
            trend_scaled = (trend_raw / 10) * 4  # 0-4
            technical_raw_total += trend_scaled
            technical_max_possible += 4.0
        else:
            trend_scaled = 0.0

        if not sr_missing:
            sr_raw = calc_support_resistance_score(current_price, low_52w, high_52w)  # 0-10
            sr_scaled = (sr_raw / 10) * 3  # 0-3
            technical_raw_total += sr_scaled
            technical_max_possible += 3.0
        else:
            sr_scaled = 0.0

        if not adx_missing:
            adx_raw = calc_adx_score(adx)  # 0-5
            adx_scaled = (adx_raw / 5) * 3  # 0-3
            technical_raw_total += adx_scaled
            technical_max_possible += 3.0
        else:
            adx_scaled = 0.0

        if technical_max_possible > 0:
            technical_normalized = (technical_raw_total / technical_max_possible) * 100
            technical_weighted = (technical_normalized / 100) * self.weights["technical"]
            technical_has_data = True
        else:
            technical_normalized = 50.0
            technical_weighted = 0.0
            technical_has_data = False

        technical = CategoryScore(
            name="technical",
            score=round(technical_normalized, 1),
            max_score=self.weights["technical"],
            weighted_score=round((technical_normalized / 100) * self.weights["technical"], 1),
            details={
                "trend": round(trend_scaled, 2),
                "support_resistance": round(sr_scaled, 2),
                "adx": round(adx_scaled, 2),
                "ma20_value": round(ma20, 0) if ma20 else None,
                "ma60_value": round(ma60, 0) if ma60 else None,
                "adx_value": round(adx, 1) if adx else None,
                "current_price": round(current_price, 0) if current_price else None,
                "low_52w": round(low_52w, 0) if low_52w else None,
                "high_52w": round(high_52w, 0) if high_52w else None,
                "position_52w": round(position_52w, 1) if position_52w else None,
            }
        )

        # =================================================================
        # 6. 섹터 (10점): 섹터순위(5) + 섹터모멘텀(5)
        # =================================================================
        rank_missing = sector_rank is None or sector_total is None
        sector_mom_missing = sector_return_5d is None

        sector_raw_total = 0.0
        sector_max_possible = 0.0

        if not rank_missing:
            rank_raw = calc_sector_rank_score(sector_rank, sector_total)  # 0-5
            sector_raw_total += rank_raw
            sector_max_possible += 5.0
        else:
            rank_raw = 0.0

        if not sector_mom_missing:
            sector_mom_raw = calc_sector_momentum_score(sector_return_5d)  # 0-5
            sector_raw_total += sector_mom_raw
            sector_max_possible += 5.0
        else:
            sector_mom_raw = 0.0

        if sector_max_possible > 0:
            sector_normalized = (sector_raw_total / sector_max_possible) * 100
            sector_weighted = (sector_normalized / 100) * self.weights["sector"]
            sector_has_data = True
        else:
            sector_normalized = 50.0
            sector_weighted = 0.0
            sector_has_data = False

        sector_cat = CategoryScore(
            name="sector",
            score=round(sector_normalized, 1),
            max_score=self.weights["sector"],
            weighted_score=round((sector_normalized / 100) * self.weights["sector"], 1),
            details={
                "sector_rank": round(rank_raw, 2),
                "sector_momentum": round(sector_mom_raw, 2),
                "sector_rank_value": sector_rank,
                "sector_total_value": sector_total,
                "sector_return_5d": round(sector_return_5d, 2) if sector_return_5d else None,
            }
        )

        # =================================================================
        # 7. 리스크 (10점): 변동성(4) + 베타(3) + 하방리스크(3)
        # =================================================================
        vol_missing = atr_pct is None
        beta_missing = beta is None
        downside_missing = max_drawdown_pct is None

        risk_raw_total = 0.0
        risk_max_possible = 0.0

        if not vol_missing:
            volatility_raw = calc_volatility_score(atr_pct)  # 0-4
            risk_raw_total += volatility_raw
            risk_max_possible += 4.0
        else:
            volatility_raw = 0.0

        if not beta_missing:
            beta_raw = calc_beta_score(beta)  # 0-3
            risk_raw_total += beta_raw
            risk_max_possible += 3.0
        else:
            beta_raw = 0.0

        if not downside_missing:
            downside_raw = calc_downside_risk_score(max_drawdown_pct)  # 0-3
            risk_raw_total += downside_raw
            risk_max_possible += 3.0
        else:
            downside_raw = 0.0

        if risk_max_possible > 0:
            risk_normalized = (risk_raw_total / risk_max_possible) * 100
            risk_weighted = (risk_normalized / 100) * self.weights["risk"]
            risk_has_data = True
        else:
            risk_normalized = 50.0
            risk_weighted = 0.0
            risk_has_data = False

        risk = CategoryScore(
            name="risk",
            score=round(risk_normalized, 1),
            max_score=self.weights["risk"],
            weighted_score=round((risk_normalized / 100) * self.weights["risk"], 1),
            details={
                "volatility": round(volatility_raw, 2),
                "beta": round(beta_raw, 2),
                "downside_risk": round(downside_raw, 2),
                "atr_pct_value": round(atr_pct, 2) if atr_pct else None,
                "beta_value": round(beta, 2) if beta else None,
                "max_drawdown_value": round(max_drawdown_pct, 2) if max_drawdown_pct else None,
            }
        )

        # =================================================================
        # 8. 주주환원 (5점): 배당수익률(5)
        # =================================================================
        div_missing = dividend_yield is None

        shareholder_raw_total = 0.0
        shareholder_max_possible = 0.0

        if not div_missing:
            dividend_raw = calc_dividend_yield_score(dividend_yield)  # 0-5
            shareholder_raw_total += dividend_raw
            shareholder_max_possible += 5.0
        else:
            dividend_raw = 0.0

        if shareholder_max_possible > 0:
            shareholder_normalized = (shareholder_raw_total / shareholder_max_possible) * 100
            shareholder_weighted = (shareholder_normalized / 100) * self.weights["shareholder"]
            shareholder_has_data = True
        else:
            shareholder_normalized = 50.0
            shareholder_weighted = 0.0
            shareholder_has_data = False

        shareholder = CategoryScore(
            name="shareholder",
            score=round(shareholder_normalized, 1),
            max_score=self.weights["shareholder"],
            weighted_score=round((shareholder_normalized / 100) * self.weights["shareholder"], 1),
            details={
                "dividend_yield": round(dividend_raw, 2),
                "dividend_yield_value": round(dividend_yield, 2) if dividend_yield else None,
            }
        )

        # =================================================================
        # 2단계 리스케일링: 결측 카테고리를 제외한 분모 재조정 (H3 해결)
        # =================================================================
        categories_data = [
            (valuation_weighted, self.weights["valuation"], valuation_has_data),
            (fundamental_weighted, self.weights["fundamental"], fundamental_has_data),
            (supply_weighted, self.weights["supply"], supply_has_data),
            (momentum_weighted, self.weights["momentum"], momentum_has_data),
            (technical_weighted, self.weights["technical"], technical_has_data),
            (sector_weighted, self.weights["sector"], sector_has_data),
            (risk_weighted, self.weights["risk"], risk_has_data),
            (shareholder_weighted, self.weights["shareholder"], shareholder_has_data),
        ]

        sum_weighted_scores = 0.0
        sum_weights = 0.0

        for w_score, weight, has_data in categories_data:
            if has_data:
                sum_weighted_scores += w_score
                sum_weights += weight

        if sum_weights > 0:
            total_score = (sum_weighted_scores / sum_weights) * 100
        else:
            total_score = 50.0  # 모두 결측인 경우 50점 중간값 폴백

        # 투자 등급 판정
        grade = get_investment_grade(total_score)

        # V3에서도 기존 V2 필드 호환을 위해 market, relative_strength 생성 (API 호환성 유지)
        news_score = calc_news_score(avg_sentiment)
        analyst_score = calc_analyst_score(target_price, current_price)
        market_raw_total = news_score + (sector_mom_raw if sector_mom_raw is not None else 2.5) + analyst_score
        market_normalized = (market_raw_total / 20) * 100

        market = CategoryScore(
            name="market",
            score=round(market_normalized, 1),
            max_score=15,  # V2 기준
            weighted_score=round((market_normalized / 100) * 15, 1),
            details={
                "news": round(news_score, 2),
                "sector_momentum": round(sector_mom_raw, 2) if sector_mom_raw is not None else 2.5,
                "analyst": round(analyst_score, 2),
            }
        )

        alpha = None
        if stock_return_20d is not None and market_return_20d is not None:
            alpha = stock_return_20d - market_return_20d

        alpha_score = calc_alpha_score(stock_return_20d, market_return_20d)
        rs_raw_total = (rank_raw if rank_raw is not None else 2.5) + alpha_score
        rs_normalized = (rs_raw_total / 10) * 100

        relative_strength = CategoryScore(
            name="relative_strength",
            score=round(rs_normalized, 1),
            max_score=10,  # V2 기준
            weighted_score=round((rs_normalized / 100) * 10, 1),
            details={
                "sector_rank": round(rank_raw, 2) if rank_raw is not None else 2.5,
                "alpha": round(alpha_score, 2),
                "sector_rank_value": sector_rank,
                "sector_total_value": sector_total,
                "stock_return_value": round(stock_return_20d, 2) if stock_return_20d else None,
                "market_return_value": round(market_return_20d, 2) if market_return_20d else None,
                "alpha_value": round(alpha, 2) if alpha else None,
            }
        )

        return RubricResult(
            symbol=symbol,
            name=name,
            technical=technical,
            supply=supply,
            fundamental=fundamental,
            market=market,
            risk=risk,
            relative_strength=relative_strength,
            valuation=valuation,
            momentum=momentum,
            sector=sector_cat,
            shareholder=shareholder,
            total_score=round(total_score, 1),
            grade=grade,
            rubric_version="v3",
        )


# =============================================================================
# 점수 계산 함수들 - 리스크 평가 (10점) - 신규
# =============================================================================


def calc_volatility_score(atr_pct: Optional[float]) -> float:
    """
    ATR 기반 변동성 점수 계산 (4점 만점)

    낮은 변동성일수록 안정적인 투자 대상으로 평가합니다.

    Args:
        atr_pct: ATR 퍼센트 (현재가 대비 ATR 비율, %)

    Returns:
        0.0 ~ 4.0 사이의 점수
    """
    if atr_pct is None:
        return 2.0  # 데이터 없으면 중간값

    if atr_pct <= 2:
        return 4.0  # 저변동성 (안정적)
    elif atr_pct <= 3:
        return 3.0  # 보통
    elif atr_pct <= 5:
        return 2.0  # 고변동성
    else:
        return 1.0  # 초고변동성 (위험)


def calc_beta_score(beta: Optional[float]) -> float:
    """
    베타 점수 계산 (3점 만점)

    베타가 1에 가까울수록 시장과 유사한 움직임을 보여 안정적으로 평가합니다.

    Args:
        beta: 베타 값 (시장 대비 민감도)

    Returns:
        0.0 ~ 3.0 사이의 점수
    """
    if beta is None:
        return 1.5  # 데이터 없으면 중간값

    if 0.8 <= beta <= 1.2:
        return 3.0  # 시장과 유사
    elif 0.5 <= beta < 0.8:
        return 2.5  # 방어적
    elif 1.2 < beta <= 1.5:
        return 2.0  # 공격적
    elif beta < 0.5:
        return 1.5  # 너무 방어적
    else:
        return 1.0  # 너무 공격적


def calc_downside_risk_score(max_drawdown_pct: Optional[float]) -> float:
    """
    최대 낙폭 기반 하방 리스크 점수 계산 (3점 만점)

    최대 낙폭이 작을수록 리스크가 낮다고 평가합니다.

    Args:
        max_drawdown_pct: 최대 낙폭 (%, 양수로 표현)

    Returns:
        0.0 ~ 3.0 사이의 점수
    """
    if max_drawdown_pct is None:
        return 1.5  # 데이터 없으면 중간값

    if max_drawdown_pct <= 10:
        return 3.0  # 낮은 리스크
    elif max_drawdown_pct <= 20:
        return 2.0  # 보통
    elif max_drawdown_pct <= 30:
        return 1.0  # 높은 리스크
    else:
        return 0.0  # 매우 높은 리스크


# =============================================================================
# 점수 계산 함수들 - 상대 강도 (10점) - 신규
# =============================================================================


def calc_sector_rank_score(rank: Optional[int], total: Optional[int]) -> float:
    """
    섹터 내 순위 점수 계산 (5점 만점)

    섹터 내에서 상위 순위일수록 높은 점수를 부여합니다.

    Args:
        rank: 섹터 내 순위 (1부터 시작)
        total: 섹터 내 전체 종목 수

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if rank is None or total is None or total == 0:
        return 2.5  # 데이터 없으면 중간값

    percentile = rank / total

    if percentile <= 0.1:
        return 5.0  # 상위 10%
    elif percentile <= 0.25:
        return 4.0  # 상위 25%
    elif percentile <= 0.5:
        return 3.0  # 상위 50%
    elif percentile <= 0.75:
        return 2.0  # 하위 50%
    else:
        return 1.0  # 하위 25%


def calc_alpha_score(stock_return: Optional[float], market_return: Optional[float]) -> float:
    """
    시장 대비 알파 점수 계산 (5점 만점)

    시장 대비 초과 수익률을 기반으로 점수를 부여합니다.

    Args:
        stock_return: 종목 수익률 (%)
        market_return: 시장 수익률 (%)

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if stock_return is None or market_return is None:
        return 2.5  # 데이터 없으면 중간값

    alpha = stock_return - market_return

    if alpha >= 10:
        return 5.0  # 시장 대비 +10%
    elif alpha >= 5:
        return 4.0  # 시장 대비 +5%
    elif alpha >= 0:
        return 3.0  # 시장과 유사
    elif alpha >= -5:
        return 2.0  # 시장 대비 -5%
    else:
        return 1.0  # 시장 대비 -10%


# =============================================================================
# 점수 계산 함수들 - 기술적 분석 확장 (MACD, ADX)
# =============================================================================


def calc_macd_score(macd: Optional[float], signal: Optional[float]) -> float:
    """
    MACD 점수 계산 (5점 만점)

    MACD와 시그널 라인의 관계를 기반으로 추세를 평가합니다.

    Args:
        macd: MACD 값
        signal: 시그널 라인 값

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if macd is None or signal is None:
        return 2.5  # 데이터 없으면 중간값

    diff = macd - signal

    if diff > 0 and macd > 0:
        return 5.0  # 강한 상승 신호 (MACD > 0, MACD > Signal)
    elif diff > 0 and macd <= 0:
        return 4.0  # 상승 전환 (MACD < 0이지만 Signal 돌파)
    elif diff == 0:
        return 3.0  # 중립
    elif diff < 0 and macd > 0:
        return 2.0  # 하락 전환 (MACD > 0이지만 Signal 아래)
    else:
        return 1.0  # 강한 하락 신호 (MACD < 0, MACD < Signal)


def calc_adx_score(adx: Optional[float]) -> float:
    """
    ADX 점수 계산 (5점 만점)

    ADX(Average Directional Index)로 추세의 강도를 평가합니다.
    ADX가 높을수록 명확한 추세가 있음을 의미합니다.

    Args:
        adx: ADX 값 (0-100)

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if adx is None:
        return 2.5  # 데이터 없으면 중간값

    if adx >= 40:
        return 5.0  # 매우 강한 추세
    elif adx >= 30:
        return 4.0  # 강한 추세
    elif adx >= 20:
        return 3.0  # 보통 추세
    elif adx >= 15:
        return 2.0  # 약한 추세
    else:
        return 1.0  # 추세 없음 (횡보)


# =============================================================================
# 점수 계산 함수들 - 밸류에이션 확장 (PBR, ROE)
# =============================================================================


def calc_pbr_score(pbr: Optional[float], sector_avg_pbr: Optional[float] = None) -> float:
    """
    PBR 점수 계산 (5점 만점)

    업종 평균 PBR 대비 현재 PBR을 비교합니다.

    Args:
        pbr: 현재 PBR
        sector_avg_pbr: 업종 평균 PBR (기본값 1.0)

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if pbr is None:
        return 2.5  # 데이터 없음
    if pbr < 0:
        return 0.0  # 자본잠식

    if sector_avg_pbr is None or sector_avg_pbr <= 0:
        sector_avg_pbr = 1.0  # 기본값

    ratio = pbr / sector_avg_pbr

    if ratio <= 0.5:
        return 5.0  # 매우 저평가
    elif ratio <= 0.7:
        return 4.0  # 저평가
    elif ratio <= 1.0:
        return 3.0  # 적정
    elif ratio <= 1.3:
        return 2.0  # 고평가
    else:
        return 1.0  # 매우 고평가


def calc_roe_score(roe: Optional[float]) -> float:
    """
    ROE 점수 계산 (5점 만점)

    자기자본이익률(ROE)로 수익성을 평가합니다.
    - 30% 이상: 최우수 (글로벌 경쟁력)
    - 20% 이상: 우수
    - 15% 이상: 양호

    Args:
        roe: ROE (%)

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if roe is None:
        return 2.5  # 데이터 없으면 중간값

    if roe >= 30:
        return 5.0  # 최우수 (글로벌 경쟁력)
    elif roe >= 20:
        return 4.5  # 우수
    elif roe >= 15:
        return 4.0  # 양호
    elif roe >= 10:
        return 3.0  # 보통
    elif roe >= 5:
        return 2.0  # 미흡
    elif roe >= 0:
        return 1.0  # 저조
    else:
        return 0.0  # 적자


# =============================================================================
# 점수 계산 함수들 - V3 주주환원 (5점)
# =============================================================================


def calc_dividend_yield_score(dividend_yield: Optional[float]) -> float:
    """
    배당수익률 점수 계산 (5점 만점)

    배당수익률이 높을수록 주주환원 정책이 좋다고 평가합니다.
    - 5% 이상: 최우수 (고배당)
    - 3% 이상: 우수
    - 2% 이상: 양호
    - 1% 이상: 보통
    - 0% 초과: 미흡

    Args:
        dividend_yield: 배당수익률 (%)

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if dividend_yield is None:
        return 2.5  # 데이터 없으면 중간값

    if dividend_yield >= 5:
        return 5.0  # 고배당
    elif dividend_yield >= 3:
        return 4.0  # 우수
    elif dividend_yield >= 2:
        return 3.0  # 양호
    elif dividend_yield >= 1:
        return 2.0  # 보통
    elif dividend_yield > 0:
        return 1.0  # 미흡
    else:
        return 0.0  # 무배당
