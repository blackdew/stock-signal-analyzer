"""
Rubric Engine

투자 기회를 평가하기 위한 루브릭 시스템.
기술적 분석, 수급 분석, 펀더멘털 분석, 시장 환경 분석을 통합하여
종합 투자 점수를 산출합니다.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.config import RUBRIC_WEIGHTS, RUBRIC_WEIGHTS_V1, get_grade_from_score


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

    # 최종 결과
    total_score: float = 0.0  # 0-100 합계
    grade: str = "Hold"       # Strong Buy, Buy, Hold, Sell, Strong Sell

    # 버전 정보
    rubric_version: str = "v2"  # v1: 4개 카테고리, v2: 6개 카테고리


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

    def __init__(self, use_v2: bool = True):
        """
        루브릭 엔진 초기화

        Args:
            use_v2: True면 V2 (6개 카테고리), False면 V1 (4개 카테고리)
        """
        self.use_v2 = use_v2
        self.weights = RUBRIC_WEIGHTS if use_v2 else RUBRIC_WEIGHTS_V1

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

        Returns:
            RubricResult 객체
        """
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

        return CategoryScore(
            name="relative_strength",
            score=round(normalized_score, 1),
            max_score=weight,
            weighted_score=round(weighted_score, 1),
            details={
                "sector_rank": rank_score,
                "alpha": alpha_score,
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

    Args:
        roe: ROE (%)

    Returns:
        0.0 ~ 5.0 사이의 점수
    """
    if roe is None:
        return 2.5  # 데이터 없으면 중간값

    if roe >= 20:
        return 5.0  # 우수
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
