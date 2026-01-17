"""
루브릭 평가 시스템 테스트

RubricEngine의 점수 계산 로직을 검증합니다.
"""

import pytest
from dataclasses import dataclass
from typing import List, Optional

from src.core.rubric import (
    # 점수 계산 함수들
    calc_trend_score,
    calc_rsi_score,
    calc_support_resistance_score,
    calc_foreign_score,
    calc_institution_score,
    calc_trading_value_score,
    calc_per_score,
    calc_growth_score,
    calc_debt_score,
    calc_news_score,
    calc_sector_momentum_score,
    calc_analyst_score,
    # 투자 등급
    get_investment_grade,
    # 엔진
    RubricEngine,
    RubricResult,
)


# =============================================================================
# Mock 데이터 클래스 (Phase 1 에이전트 데이터 구조 모방)
# =============================================================================


@dataclass
class MockMarketData:
    """MarketData Mock"""
    symbol: str = "005930"
    name: str = "삼성전자"
    market: str = "KOSPI"
    current_price: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    rsi: Optional[float] = None
    foreign_net_buy: Optional[List[float]] = None
    institution_net_buy: Optional[List[float]] = None
    trading_value: Optional[float] = None


@dataclass
class MockFundamentalData:
    """FundamentalData Mock"""
    symbol: str = "005930"
    name: str = "삼성전자"
    per: Optional[float] = None
    sector_avg_per: Optional[float] = None
    operating_profit_growth: Optional[float] = None
    debt_ratio: Optional[float] = None


@dataclass
class MockNewsData:
    """NewsData Mock"""
    symbol: str = "005930"
    name: str = "삼성전자"
    avg_sentiment_score: Optional[float] = None


# =============================================================================
# 추세 점수 테스트 (calc_trend_score)
# =============================================================================


class TestTrendScore:
    """추세 점수 계산 테스트"""

    def test_strong_uptrend(self):
        """강한 상승 추세: MA20이 MA60보다 5% 이상 높음"""
        assert calc_trend_score(1050, 1000) == 10.0  # 5% 상승

    def test_uptrend(self):
        """상승 추세: MA20이 MA60보다 2~5% 높음"""
        assert calc_trend_score(1030, 1000) == 8.0  # 3% 상승

    def test_weak_uptrend(self):
        """약한 상승/횡보: MA20이 MA60보다 0~2% 높음"""
        assert calc_trend_score(1010, 1000) == 6.0  # 1% 상승

    def test_weak_downtrend(self):
        """약한 하락: MA20이 MA60보다 0~2% 낮음"""
        assert calc_trend_score(990, 1000) == 4.0  # 1% 하락

    def test_downtrend(self):
        """하락 추세: MA20이 MA60보다 2~5% 낮음"""
        assert calc_trend_score(970, 1000) == 2.0  # 3% 하락

    def test_strong_downtrend(self):
        """강한 하락 추세: MA20이 MA60보다 5% 이상 낮음"""
        assert calc_trend_score(940, 1000) == 0.0  # 6% 하락

    def test_missing_ma20(self):
        """MA20 데이터 없음"""
        assert calc_trend_score(None, 1000) == 5.0

    def test_missing_ma60(self):
        """MA60 데이터 없음"""
        assert calc_trend_score(1100, None) == 5.0

    def test_both_missing(self):
        """MA20, MA60 모두 없음"""
        assert calc_trend_score(None, None) == 5.0

    def test_ma60_zero(self):
        """MA60이 0인 경우 (division by zero 방지)"""
        assert calc_trend_score(1000, 0) == 5.0


# =============================================================================
# RSI 점수 테스트 (calc_rsi_score)
# =============================================================================


class TestRsiScore:
    """RSI 점수 계산 테스트"""

    def test_optimal_range(self):
        """최적 구간: RSI 40~60"""
        assert calc_rsi_score(50) == 10.0
        assert calc_rsi_score(40) == 10.0
        assert calc_rsi_score(60) == 10.0

    def test_oversold_recovery(self):
        """과매도 탈출 구간: RSI 30~40"""
        assert calc_rsi_score(35) == 8.0

    def test_upward_momentum(self):
        """상승 모멘텀: RSI 60~70"""
        assert calc_rsi_score(65) == 7.0

    def test_oversold(self):
        """과매도: RSI 20~30"""
        assert calc_rsi_score(25) == 6.0

    def test_overbought_warning(self):
        """과매수 주의: RSI 70~80"""
        assert calc_rsi_score(75) == 4.0

    def test_extreme_oversold(self):
        """극단적 과매도: RSI < 20"""
        assert calc_rsi_score(15) == 3.0

    def test_extreme_overbought(self):
        """극단적 과매수: RSI > 80"""
        assert calc_rsi_score(85) == 1.0

    def test_missing_rsi(self):
        """RSI 데이터 없음"""
        assert calc_rsi_score(None) == 5.0

    def test_rsi_clamping(self):
        """RSI 범위 클램핑 (0-100)"""
        assert calc_rsi_score(-10) == 3.0  # 극단적 과매도로 처리
        assert calc_rsi_score(110) == 1.0  # 극단적 과매수로 처리


# =============================================================================
# 지지/저항 점수 테스트 (calc_support_resistance_score)
# =============================================================================


class TestSupportResistanceScore:
    """지지/저항 점수 계산 테스트"""

    def test_at_bottom(self):
        """바닥권: 52주 범위의 0~20%"""
        # 현재가 105 (최저 100, 최고 200) → position = 5/100 = 0.05
        assert calc_support_resistance_score(105, 100, 200) == 10.0

    def test_near_bottom(self):
        """저점 근처: 52주 범위의 20~40%"""
        # 현재가 130 (최저 100, 최고 200) → position = 30/100 = 0.3
        assert calc_support_resistance_score(130, 100, 200) == 8.0

    def test_middle(self):
        """중간: 52주 범위의 40~60%"""
        # 현재가 150 (최저 100, 최고 200) → position = 50/100 = 0.5
        assert calc_support_resistance_score(150, 100, 200) == 6.0

    def test_near_top(self):
        """고점 근처: 52주 범위의 60~80%"""
        # 현재가 170 (최저 100, 최고 200) → position = 70/100 = 0.7
        assert calc_support_resistance_score(170, 100, 200) == 4.0

    def test_at_ceiling(self):
        """천장권: 52주 범위의 80~100%"""
        # 현재가 195 (최저 100, 최고 200) → position = 95/100 = 0.95
        assert calc_support_resistance_score(195, 100, 200) == 2.0

    def test_missing_current_price(self):
        """현재가 데이터 없음"""
        assert calc_support_resistance_score(None, 100, 200) == 5.0

    def test_missing_low_52w(self):
        """52주 최저가 데이터 없음"""
        assert calc_support_resistance_score(150, None, 200) == 5.0

    def test_missing_high_52w(self):
        """52주 최고가 데이터 없음"""
        assert calc_support_resistance_score(150, 100, None) == 5.0

    def test_equal_high_low(self):
        """52주 고가 = 저가 (division by zero 방지)"""
        assert calc_support_resistance_score(100, 100, 100) == 5.0


# =============================================================================
# 외국인/기관 순매수 점수 테스트
# =============================================================================


class TestForeignScore:
    """외국인 순매수 점수 계산 테스트"""

    def test_five_consecutive_buy(self):
        """5일 연속 순매수"""
        assert calc_foreign_score([100, 50, 30, 20, 10]) == 10.0

    def test_four_consecutive_buy(self):
        """4일 연속 순매수"""
        assert calc_foreign_score([100, 50, 30, 20, -10]) == 8.0

    def test_three_consecutive_buy(self):
        """3일 연속 순매수"""
        assert calc_foreign_score([100, 50, 30, -20, -10]) == 6.0

    def test_two_consecutive_buy(self):
        """2일 연속 순매수"""
        assert calc_foreign_score([100, 50, -30, -20, -10]) == 4.0

    def test_one_buy(self):
        """1일 순매수"""
        assert calc_foreign_score([100, -50, -30, -20, -10]) == 2.0

    def test_no_buy(self):
        """순매수 없음"""
        assert calc_foreign_score([-100, -50, -30, -20, -10]) == 0.0

    def test_empty_list(self):
        """빈 리스트"""
        assert calc_foreign_score([]) == 5.0

    def test_none(self):
        """None"""
        assert calc_foreign_score(None) == 5.0


class TestInstitutionScore:
    """기관 순매수 점수 계산 테스트"""

    def test_five_consecutive_buy(self):
        """5일 연속 순매수"""
        assert calc_institution_score([100, 50, 30, 20, 10]) == 10.0

    def test_no_buy(self):
        """순매수 없음"""
        assert calc_institution_score([-100, -50, -30, -20, -10]) == 0.0

    def test_none(self):
        """None"""
        assert calc_institution_score(None) == 5.0


class TestTradingValueScore:
    """거래대금 점수 계산 테스트"""

    def test_high_volume(self):
        """거래 폭증: 평균의 2배 이상"""
        assert calc_trading_value_score(200, 100) == 5.0

    def test_increased_volume(self):
        """거래 증가: 평균의 1.5~2배"""
        assert calc_trading_value_score(150, 100) == 4.0

    def test_average_volume(self):
        """평균 수준: 평균의 1~1.5배"""
        assert calc_trading_value_score(100, 100) == 3.0

    def test_decreased_volume(self):
        """거래 감소: 평균의 0.5~1배"""
        assert calc_trading_value_score(70, 100) == 2.0

    def test_very_low_volume(self):
        """거래 급감: 평균의 0.5배 미만"""
        assert calc_trading_value_score(30, 100) == 1.0

    def test_missing_trading_value(self):
        """당일 거래대금 없음"""
        assert calc_trading_value_score(None, 100) == 2.5

    def test_missing_avg(self):
        """평균 거래대금 없음"""
        assert calc_trading_value_score(100, None) == 2.5

    def test_zero_avg(self):
        """평균 거래대금 0 (division by zero 방지)"""
        assert calc_trading_value_score(100, 0) == 2.5


# =============================================================================
# PER 점수 테스트 (calc_per_score)
# =============================================================================


class TestPerScore:
    """PER 점수 계산 테스트"""

    def test_very_undervalued(self):
        """매우 저평가: 업종 평균의 50% 이하"""
        assert calc_per_score(7.5, 15) == 10.0  # ratio = 0.5

    def test_undervalued(self):
        """저평가: 업종 평균의 50~70%"""
        assert calc_per_score(9, 15) == 8.0  # ratio = 0.6

    def test_fair_value(self):
        """적정~약간 저평가: 업종 평균의 70~100%"""
        assert calc_per_score(12, 15) == 6.0  # ratio = 0.8

    def test_slightly_overvalued(self):
        """약간 고평가: 업종 평균의 100~130%"""
        assert calc_per_score(18, 15) == 4.0  # ratio = 1.2

    def test_overvalued(self):
        """고평가: 업종 평균의 130~150%"""
        assert calc_per_score(21, 15) == 2.0  # ratio = 1.4

    def test_very_overvalued(self):
        """매우 고평가: 업종 평균의 150% 초과"""
        assert calc_per_score(24, 15) == 0.0  # ratio = 1.6

    def test_negative_per(self):
        """적자 기업 (음수 PER)"""
        assert calc_per_score(-10, 15) == 0.0

    def test_missing_per(self):
        """PER 데이터 없음"""
        assert calc_per_score(None, 15) == 5.0

    def test_missing_sector_avg(self):
        """업종 평균 PER 없음 (기본값 15 사용)"""
        assert calc_per_score(7.5, None) == 10.0  # ratio = 0.5 (기본값 15)

    def test_zero_sector_avg(self):
        """업종 평균 PER 0 (기본값 15 사용)"""
        assert calc_per_score(7.5, 0) == 10.0


# =============================================================================
# 성장성 점수 테스트 (calc_growth_score)
# =============================================================================


class TestGrowthScore:
    """영업이익 성장률 점수 계산 테스트"""

    def test_high_growth(self):
        """고성장: 30% 이상"""
        assert calc_growth_score(35) == 10.0

    def test_growth(self):
        """성장: 20~30%"""
        assert calc_growth_score(25) == 8.0

    def test_moderate_growth(self):
        """완만한 성장: 10~20%"""
        assert calc_growth_score(15) == 6.0

    def test_stagnant(self):
        """정체: 0~10%"""
        assert calc_growth_score(5) == 4.0

    def test_negative_growth(self):
        """역성장: -10~0%"""
        assert calc_growth_score(-5) == 2.0

    def test_severe_decline(self):
        """급격한 역성장: -10% 미만"""
        assert calc_growth_score(-20) == 0.0

    def test_missing_growth(self):
        """성장률 데이터 없음"""
        assert calc_growth_score(None) == 5.0


# =============================================================================
# 부채비율 점수 테스트 (calc_debt_score)
# =============================================================================


class TestDebtScore:
    """부채비율 점수 계산 테스트"""

    def test_very_healthy(self):
        """매우 건전: 50% 이하"""
        assert calc_debt_score(40) == 5.0

    def test_healthy(self):
        """건전: 50~100%"""
        assert calc_debt_score(80) == 4.0

    def test_moderate(self):
        """보통: 100~150%"""
        assert calc_debt_score(120) == 3.0

    def test_caution(self):
        """주의: 150~200%"""
        assert calc_debt_score(180) == 2.0

    def test_risky(self):
        """위험: 200% 초과"""
        assert calc_debt_score(250) == 1.0

    def test_missing_debt_ratio(self):
        """부채비율 데이터 없음"""
        assert calc_debt_score(None) == 2.5


# =============================================================================
# 뉴스 센티먼트 점수 테스트 (calc_news_score)
# =============================================================================


class TestNewsScore:
    """뉴스 센티먼트 점수 계산 테스트"""

    def test_very_positive(self):
        """매우 긍정: 센티먼트 1.0"""
        assert calc_news_score(1.0) == 10.0

    def test_positive(self):
        """긍정: 센티먼트 0.5"""
        assert calc_news_score(0.5) == 7.5

    def test_neutral(self):
        """중립: 센티먼트 0.0"""
        assert calc_news_score(0.0) == 5.0

    def test_negative(self):
        """부정: 센티먼트 -0.5"""
        assert calc_news_score(-0.5) == 2.5

    def test_very_negative(self):
        """매우 부정: 센티먼트 -1.0"""
        assert calc_news_score(-1.0) == 0.0

    def test_missing_sentiment(self):
        """센티먼트 데이터 없음"""
        assert calc_news_score(None) == 5.0


# =============================================================================
# 섹터 모멘텀 점수 테스트 (calc_sector_momentum_score)
# =============================================================================


class TestSectorMomentumScore:
    """섹터 모멘텀 점수 계산 테스트"""

    def test_strong_momentum(self):
        """강한 모멘텀: 5% 이상"""
        assert calc_sector_momentum_score(7) == 5.0

    def test_good_momentum(self):
        """좋은 모멘텀: 2~5%"""
        assert calc_sector_momentum_score(3) == 4.0

    def test_flat(self):
        """횡보: 0~2%"""
        assert calc_sector_momentum_score(1) == 3.0

    def test_weak_negative(self):
        """약한 하락: -2~0%"""
        assert calc_sector_momentum_score(-1) == 2.0

    def test_negative_momentum(self):
        """하락 모멘텀: -2% 미만"""
        assert calc_sector_momentum_score(-5) == 1.0

    def test_missing_momentum(self):
        """모멘텀 데이터 없음"""
        assert calc_sector_momentum_score(None) == 2.5


# =============================================================================
# 애널리스트 점수 테스트 (calc_analyst_score)
# =============================================================================


class TestAnalystScore:
    """애널리스트 점수 계산 테스트"""

    def test_high_upside(self):
        """상승 여력 큼: 30% 이상"""
        assert calc_analyst_score(130, 100) == 5.0  # 30% upside

    def test_moderate_upside(self):
        """상승 여력 있음: 15~30%"""
        assert calc_analyst_score(120, 100) == 4.0  # 20% upside

    def test_fair_value(self):
        """적정가 근처: 0~15%"""
        assert calc_analyst_score(105, 100) == 3.0  # 5% upside

    def test_slightly_overvalued(self):
        """약간 고평가: -15~0%"""
        assert calc_analyst_score(90, 100) == 2.0  # -10% upside

    def test_overvalued(self):
        """고평가: -15% 미만"""
        assert calc_analyst_score(80, 100) == 1.0  # -20% upside

    def test_missing_target(self):
        """목표가 데이터 없음"""
        assert calc_analyst_score(None, 100) == 2.5

    def test_missing_current(self):
        """현재가 데이터 없음"""
        assert calc_analyst_score(120, None) == 2.5

    def test_zero_current(self):
        """현재가 0 (division by zero 방지)"""
        assert calc_analyst_score(120, 0) == 2.5


# =============================================================================
# 투자 등급 테스트 (get_investment_grade)
# =============================================================================


class TestInvestmentGrade:
    """투자 등급 판정 테스트"""

    def test_strong_buy(self):
        """Strong Buy: 80~100점"""
        assert get_investment_grade(85) == "Strong Buy"
        assert get_investment_grade(100) == "Strong Buy"
        assert get_investment_grade(80) == "Strong Buy"

    def test_buy(self):
        """Buy: 60~79점"""
        assert get_investment_grade(70) == "Buy"
        assert get_investment_grade(79) == "Buy"
        assert get_investment_grade(60) == "Buy"

    def test_hold(self):
        """Hold: 40~59점"""
        assert get_investment_grade(55) == "Hold"
        assert get_investment_grade(59) == "Hold"
        assert get_investment_grade(40) == "Hold"

    def test_sell(self):
        """Sell: 20~39점"""
        assert get_investment_grade(30) == "Sell"
        assert get_investment_grade(39) == "Sell"
        assert get_investment_grade(20) == "Sell"

    def test_strong_sell(self):
        """Strong Sell: 0~19점"""
        assert get_investment_grade(10) == "Strong Sell"
        assert get_investment_grade(19) == "Strong Sell"
        assert get_investment_grade(0) == "Strong Sell"


# =============================================================================
# RubricEngine 통합 테스트
# =============================================================================


class TestRubricEngine:
    """RubricEngine 통합 테스트"""

    def test_calculate_with_all_data(self):
        """모든 데이터가 있는 경우"""
        engine = RubricEngine()

        market_data = MockMarketData(
            current_price=100000,
            ma20=105000,  # 5% 상승 추세
            ma60=100000,
            rsi=50,  # 최적 구간
            foreign_net_buy=[100, 50, 30, 20, 10],  # 5일 연속
            institution_net_buy=[100, 50, 30, 20, 10],  # 5일 연속
            trading_value=200,  # 폭증
        )

        fundamental_data = MockFundamentalData(
            per=7.5,  # 매우 저평가
            sector_avg_per=15,
            operating_profit_growth=35,  # 고성장
            debt_ratio=40,  # 매우 건전
        )

        news_data = MockNewsData(
            avg_sentiment_score=0.5,  # 긍정
        )

        result = engine.calculate(
            symbol="005930",
            name="삼성전자",
            market_data=market_data,
            fundamental_data=fundamental_data,
            news_data=news_data,
            low_52w=80000,  # 현재가 100000, 52주 저가 80000, 고가 150000
            high_52w=150000,  # position = (100000-80000)/(150000-80000) = 20000/70000 ≈ 0.29 (저점 근처)
            sector_return_5d=3,  # 좋은 모멘텀
            target_price=130000,  # 30% upside
        )

        assert isinstance(result, RubricResult)
        assert result.symbol == "005930"
        assert result.name == "삼성전자"
        assert result.total_score > 0
        assert result.grade in ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]

        # 카테고리별 점수 확인
        assert result.technical.name == "technical"
        assert result.supply.name == "supply"
        assert result.fundamental.name == "fundamental"
        assert result.market.name == "market"

    def test_calculate_with_missing_data(self):
        """데이터가 없는 경우 (모든 항목 중간값)"""
        engine = RubricEngine()

        result = engine.calculate(
            symbol="005930",
            name="삼성전자",
        )

        # 모든 항목 중간값 = 50점
        assert result.total_score == 50.0
        assert result.grade == "Hold"

    def test_calculate_with_partial_data(self):
        """일부 데이터만 있는 경우"""
        engine = RubricEngine()

        market_data = MockMarketData(
            ma20=105000,
            ma60=100000,
            rsi=50,
        )

        result = engine.calculate(
            symbol="005930",
            name="삼성전자",
            market_data=market_data,
        )

        # 기술적 분석은 높은 점수, 나머지는 중간값
        assert result.technical.score > 50
        assert result.supply.score == 50.0  # 데이터 없음 (foreign/inst = 5, tv = 2.5 → 12.5/25 * 100 = 50)
        assert result.fundamental.score == 50.0
        assert result.market.score == 50.0

    def test_calculate_with_all_missing_data(self):
        """calculate_with_all_missing_data 메서드 테스트"""
        engine = RubricEngine()

        result = engine.calculate_with_all_missing_data(
            symbol="005930",
            name="삼성전자",
        )

        assert result.total_score == 50.0
        assert result.grade == "Hold"

    def test_weighted_scores_sum_to_total(self):
        """가중치 적용 점수의 합이 총점과 일치"""
        engine = RubricEngine()

        market_data = MockMarketData(
            current_price=100000,
            ma20=105000,
            ma60=100000,
            rsi=50,
            foreign_net_buy=[100, 50, 30, 20, 10],
            institution_net_buy=[100, 50, 30, 20, 10],
            trading_value=200,
        )

        result = engine.calculate(
            symbol="005930",
            name="삼성전자",
            market_data=market_data,
        )

        # V2: 가중치 합계 = 25 + 20 + 20 + 15 + 10 + 10 = 100
        expected_total = (
            result.technical.weighted_score +
            result.supply.weighted_score +
            result.fundamental.weighted_score +
            result.market.weighted_score
        )

        # V2에서는 risk와 relative_strength도 포함
        if result.risk:
            expected_total += result.risk.weighted_score
        if result.relative_strength:
            expected_total += result.relative_strength.weighted_score

        assert abs(result.total_score - expected_total) < 0.1

    def test_score_range_valid(self):
        """점수가 0-100 범위 내"""
        engine = RubricEngine()

        # 최저 점수 케이스
        market_data_low = MockMarketData(
            ma20=940,  # 강한 하락 추세 (0점)
            ma60=1000,
            rsi=85,  # 극단적 과매수 (1점)
            foreign_net_buy=[-100, -50, -30, -20, -10],  # 순매수 없음 (0점)
            institution_net_buy=[-100, -50, -30, -20, -10],  # 순매수 없음 (0점)
            trading_value=30,  # 거래 급감 (1점)
        )

        result_low = engine.calculate(
            symbol="005930",
            name="삼성전자",
            market_data=market_data_low,
        )

        assert 0 <= result_low.total_score <= 100

        # 최고 점수 케이스
        market_data_high = MockMarketData(
            current_price=105,
            ma20=1050,  # 강한 상승 추세 (10점)
            ma60=1000,
            rsi=50,  # 최적 구간 (10점)
            foreign_net_buy=[100, 50, 30, 20, 10],  # 5일 연속 (10점)
            institution_net_buy=[100, 50, 30, 20, 10],  # 5일 연속 (10점)
            trading_value=200,  # 폭증 (5점)
        )

        result_high = engine.calculate(
            symbol="005930",
            name="삼성전자",
            market_data=market_data_high,
            low_52w=100,
            high_52w=200,  # 바닥권 (10점)
        )

        assert 0 <= result_high.total_score <= 100


# =============================================================================
# 엣지 케이스 테스트
# =============================================================================


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_negative_values(self):
        """음수 값 처리"""
        # 음수 PER
        assert calc_per_score(-10, 15) == 0.0

        # 음수 RSI (클램핑)
        assert calc_rsi_score(-10) == 3.0

    def test_zero_values(self):
        """0 값 처리"""
        # MA60 = 0
        assert calc_trend_score(1000, 0) == 5.0

        # 평균 거래대금 = 0
        assert calc_trading_value_score(100, 0) == 2.5

        # 현재가 = 0
        assert calc_analyst_score(120, 0) == 2.5

    def test_extreme_values(self):
        """극단적 값 처리"""
        # 매우 높은 RSI
        assert calc_rsi_score(150) == 1.0

        # 매우 높은 PER
        assert calc_per_score(1000, 15) == 0.0

        # 매우 높은 부채비율
        assert calc_debt_score(500) == 1.0
