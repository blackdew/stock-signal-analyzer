"""
Rubric Engine

투자 기회를 평가하기 위한 루브릭 시스템.
기술적 분석, 수급 분석, 펀더멘털 분석, 시장 환경 분석을 통합하여
종합 투자 점수를 산출합니다.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.config import RUBRIC_WEIGHTS, get_grade_from_score


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

    # 최종 결과
    total_score: float  # 0-100 합계
    grade: str  # Strong Buy, Buy, Hold, Sell, Strong Sell


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
    RSI 점수 계산 (10점 만점)

    RSI 40~60 구간이 가장 좋음 (추세 전환 기대).

    Args:
        rsi: RSI 값 (0-100)

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if rsi is None:
        return 5.0  # 데이터 없으면 중간값

    # RSI 범위 클램핑
    rsi = max(0, min(100, rsi))

    if 40 <= rsi <= 60:
        return 10.0  # 최적 구간
    elif 30 <= rsi < 40:
        return 8.0   # 과매도 탈출 구간
    elif 60 < rsi <= 70:
        return 7.0   # 상승 모멘텀
    elif 20 <= rsi < 30:
        return 6.0   # 과매도 (반등 기대)
    elif 70 < rsi <= 80:
        return 4.0   # 과매수 주의
    elif rsi < 20:
        return 3.0   # 극단적 과매도
    else:
        return 1.0   # 극단적 과매수 (80+)


def calc_support_resistance_score(
    current_price: Optional[float],
    low_52w: Optional[float],
    high_52w: Optional[float]
) -> float:
    """
    지지/저항 점수 계산 (10점 만점)

    현재가가 52주 범위에서 어디에 위치하는지 평가합니다.
    바닥권에 있을수록 매수 기회로 판단합니다.

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

    if position <= 0.2:
        return 10.0  # 바닥권 (매수 기회)
    elif position <= 0.4:
        return 8.0   # 저점 근처
    elif position <= 0.6:
        return 6.0   # 중간
    elif position <= 0.8:
        return 4.0   # 고점 근처
    else:
        return 2.0   # 천장권 (주의)


# =============================================================================
# 점수 계산 함수들 - 수급 분석 (25점)
# =============================================================================


def calc_foreign_score(foreign_net_buy: Optional[List[float]]) -> float:
    """
    외국인 순매수 점수 계산 (10점 만점)

    최근 5일간 외국인 연속 순매수 일수를 기반으로 점수를 계산합니다.

    Args:
        foreign_net_buy: 최근 5일 외국인 순매수 데이터 (억원)

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if not foreign_net_buy:
        return 5.0  # 데이터 없으면 중간값

    consecutive_buy = 0
    for amount in foreign_net_buy:
        if amount > 0:
            consecutive_buy += 1
        else:
            break

    score_map = {5: 10.0, 4: 8.0, 3: 6.0, 2: 4.0, 1: 2.0, 0: 0.0}
    return score_map.get(consecutive_buy, 0.0)


def calc_institution_score(institution_net_buy: Optional[List[float]]) -> float:
    """
    기관 순매수 점수 계산 (10점 만점)

    최근 5일간 기관 연속 순매수 일수를 기반으로 점수를 계산합니다.

    Args:
        institution_net_buy: 최근 5일 기관 순매수 데이터 (억원)

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if not institution_net_buy:
        return 5.0  # 데이터 없으면 중간값

    consecutive_buy = 0
    for amount in institution_net_buy:
        if amount > 0:
            consecutive_buy += 1
        else:
            break

    score_map = {5: 10.0, 4: 8.0, 3: 6.0, 2: 4.0, 1: 2.0, 0: 0.0}
    return score_map.get(consecutive_buy, 0.0)


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

    Args:
        op_growth: 영업이익 성장률 (YoY, %)

    Returns:
        0.0 ~ 10.0 사이의 점수
    """
    if op_growth is None:
        return 5.0  # 데이터 없으면 중간값

    if op_growth >= 30:
        return 10.0  # 고성장
    elif op_growth >= 20:
        return 8.0   # 성장
    elif op_growth >= 10:
        return 6.0   # 완만한 성장
    elif op_growth >= 0:
        return 4.0   # 정체
    elif op_growth >= -10:
        return 2.0   # 역성장
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
    """

    def __init__(self):
        self.weights = RUBRIC_WEIGHTS

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

        Returns:
            RubricResult 객체
        """
        # 1. 기술적 분석 점수 계산 (30점)
        technical = self._calculate_technical(market_data, low_52w, high_52w)

        # 2. 수급 분석 점수 계산 (25점)
        supply = self._calculate_supply(market_data)

        # 3. 펀더멘털 분석 점수 계산 (25점)
        fundamental = self._calculate_fundamental(fundamental_data)

        # 4. 시장 환경 점수 계산 (20점)
        market = self._calculate_market(
            news_data, market_data, sector_return_5d, target_price
        )

        # 5. 총점 계산 (가중치 적용 점수의 합)
        total_score = (
            technical.weighted_score +
            supply.weighted_score +
            fundamental.weighted_score +
            market.weighted_score
        )

        # 6. 투자 등급 판정
        grade = get_investment_grade(total_score)

        return RubricResult(
            symbol=symbol,
            name=name,
            technical=technical,
            supply=supply,
            fundamental=fundamental,
            market=market,
            total_score=round(total_score, 1),
            grade=grade,
        )

    def _calculate_technical(
        self,
        market_data: Optional[Any],
        low_52w: Optional[float],
        high_52w: Optional[float]
    ) -> CategoryScore:
        """기술적 분석 점수 계산 (30점 만점)"""
        weight = self.weights["technical"]  # 30

        # 데이터 추출
        ma20 = getattr(market_data, "ma20", None) if market_data else None
        ma60 = getattr(market_data, "ma60", None) if market_data else None
        rsi = getattr(market_data, "rsi", None) if market_data else None
        current_price = getattr(market_data, "current_price", None) if market_data else None

        # 세부 점수 계산
        trend_score = calc_trend_score(ma20, ma60)  # 0-10
        rsi_score = calc_rsi_score(rsi)  # 0-10
        sr_score = calc_support_resistance_score(current_price, low_52w, high_52w)  # 0-10

        # 정규화된 점수 (0-100)
        raw_total = trend_score + rsi_score + sr_score  # 0-30
        normalized_score = (raw_total / 30) * 100

        # 가중치 적용 점수
        weighted_score = (normalized_score / 100) * weight

        return CategoryScore(
            name="technical",
            score=round(normalized_score, 1),
            max_score=weight,
            weighted_score=round(weighted_score, 1),
            details={
                "trend": trend_score,
                "rsi": rsi_score,
                "support_resistance": sr_score,
            }
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

        return CategoryScore(
            name="supply",
            score=round(normalized_score, 1),
            max_score=weight,
            weighted_score=round(weighted_score, 1),
            details={
                "foreign": foreign_score,
                "institution": inst_score,
                "trading_value": tv_score,
            }
        )

    def _calculate_fundamental(self, fundamental_data: Optional[Any]) -> CategoryScore:
        """펀더멘털 분석 점수 계산 (25점 만점)"""
        weight = self.weights["fundamental"]  # 25

        # 데이터 추출
        per = getattr(fundamental_data, "per", None) if fundamental_data else None
        sector_avg_per = getattr(fundamental_data, "sector_avg_per", None) if fundamental_data else None
        op_growth = getattr(fundamental_data, "operating_profit_growth", None) if fundamental_data else None
        debt_ratio = getattr(fundamental_data, "debt_ratio", None) if fundamental_data else None

        # 세부 점수 계산
        per_score = calc_per_score(per, sector_avg_per)  # 0-10
        growth_score = calc_growth_score(op_growth)  # 0-10
        debt_score = calc_debt_score(debt_ratio)  # 0-5

        # 정규화된 점수 (0-100)
        raw_total = per_score + growth_score + debt_score  # 0-25
        normalized_score = (raw_total / 25) * 100

        # 가중치 적용 점수
        weighted_score = (normalized_score / 100) * weight

        return CategoryScore(
            name="fundamental",
            score=round(normalized_score, 1),
            max_score=weight,
            weighted_score=round(weighted_score, 1),
            details={
                "per": per_score,
                "growth": growth_score,
                "debt": debt_score,
            }
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
