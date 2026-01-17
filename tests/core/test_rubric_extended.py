"""
루브릭 V2 확장 기능 테스트

새로 추가된 리스크 평가, 상대 강도, MACD, ADX, PBR, ROE 점수 계산을 검증합니다.
"""

import pytest
from dataclasses import dataclass
from typing import List, Optional

from src.core.rubric import (
    # V2 신규 점수 계산 함수들
    calc_volatility_score,
    calc_beta_score,
    calc_downside_risk_score,
    calc_sector_rank_score,
    calc_alpha_score,
    calc_macd_score,
    calc_adx_score,
    calc_pbr_score,
    calc_roe_score,
    # 엔진
    RubricEngine,
    RubricResult,
)


# =============================================================================
# 변동성 점수 테스트 (calc_volatility_score)
# =============================================================================


class TestVolatilityScore:
    """변동성 점수 계산 테스트 (ATR 기반)"""

    def test_low_volatility(self):
        """저변동성: ATR <= 2%"""
        assert calc_volatility_score(1.5) == 4.0
        assert calc_volatility_score(2.0) == 4.0

    def test_moderate_volatility(self):
        """보통 변동성: 2% < ATR <= 3%"""
        assert calc_volatility_score(2.5) == 3.0

    def test_high_volatility(self):
        """고변동성: 3% < ATR <= 5%"""
        assert calc_volatility_score(4.0) == 2.0

    def test_very_high_volatility(self):
        """초고변동성: ATR > 5%"""
        assert calc_volatility_score(6.0) == 1.0

    def test_missing_atr(self):
        """ATR 데이터 없음"""
        assert calc_volatility_score(None) == 2.0


# =============================================================================
# 베타 점수 테스트 (calc_beta_score)
# =============================================================================


class TestBetaScore:
    """베타 점수 계산 테스트"""

    def test_market_like(self):
        """시장과 유사: 0.8 <= beta <= 1.2"""
        assert calc_beta_score(1.0) == 3.0
        assert calc_beta_score(0.8) == 3.0
        assert calc_beta_score(1.2) == 3.0

    def test_defensive(self):
        """방어적: 0.5 <= beta < 0.8"""
        assert calc_beta_score(0.6) == 2.5

    def test_aggressive(self):
        """공격적: 1.2 < beta <= 1.5"""
        assert calc_beta_score(1.3) == 2.0

    def test_too_defensive(self):
        """너무 방어적: beta < 0.5"""
        assert calc_beta_score(0.3) == 1.5

    def test_too_aggressive(self):
        """너무 공격적: beta > 1.5"""
        assert calc_beta_score(2.0) == 1.0

    def test_missing_beta(self):
        """베타 데이터 없음"""
        assert calc_beta_score(None) == 1.5


# =============================================================================
# 하방 리스크 점수 테스트 (calc_downside_risk_score)
# =============================================================================


class TestDownsideRiskScore:
    """하방 리스크 점수 계산 테스트 (최대 낙폭 기반)"""

    def test_low_risk(self):
        """낮은 리스크: MDD <= 10%"""
        assert calc_downside_risk_score(5.0) == 3.0
        assert calc_downside_risk_score(10.0) == 3.0

    def test_moderate_risk(self):
        """보통 리스크: 10% < MDD <= 20%"""
        assert calc_downside_risk_score(15.0) == 2.0

    def test_high_risk(self):
        """높은 리스크: 20% < MDD <= 30%"""
        assert calc_downside_risk_score(25.0) == 1.0

    def test_very_high_risk(self):
        """매우 높은 리스크: MDD > 30%"""
        assert calc_downside_risk_score(35.0) == 0.0

    def test_missing_mdd(self):
        """MDD 데이터 없음"""
        assert calc_downside_risk_score(None) == 1.5


# =============================================================================
# 섹터 순위 점수 테스트 (calc_sector_rank_score)
# =============================================================================


class TestSectorRankScore:
    """섹터 내 순위 점수 계산 테스트"""

    def test_top_10_percent(self):
        """상위 10%"""
        assert calc_sector_rank_score(1, 10) == 5.0

    def test_top_25_percent(self):
        """상위 25%"""
        assert calc_sector_rank_score(2, 10) == 4.0

    def test_top_50_percent(self):
        """상위 50%"""
        assert calc_sector_rank_score(4, 10) == 3.0

    def test_bottom_50_percent(self):
        """하위 50%"""
        assert calc_sector_rank_score(7, 10) == 2.0

    def test_bottom_25_percent(self):
        """하위 25%"""
        assert calc_sector_rank_score(9, 10) == 1.0

    def test_missing_rank(self):
        """순위 데이터 없음"""
        assert calc_sector_rank_score(None, 10) == 2.5
        assert calc_sector_rank_score(1, None) == 2.5

    def test_zero_total(self):
        """전체 종목 수 0"""
        assert calc_sector_rank_score(1, 0) == 2.5


# =============================================================================
# 알파 점수 테스트 (calc_alpha_score)
# =============================================================================


class TestAlphaScore:
    """시장 대비 알파 점수 계산 테스트"""

    def test_high_alpha(self):
        """시장 대비 +10% 이상"""
        assert calc_alpha_score(15.0, 5.0) == 5.0  # alpha = 10%

    def test_moderate_alpha(self):
        """시장 대비 +5%~10%"""
        assert calc_alpha_score(10.0, 5.0) == 4.0  # alpha = 5%

    def test_market_like(self):
        """시장과 유사: 0%~5%"""
        assert calc_alpha_score(7.0, 5.0) == 3.0  # alpha = 2%

    def test_slight_underperform(self):
        """시장 대비 -5%~0%"""
        assert calc_alpha_score(3.0, 5.0) == 2.0  # alpha = -2%

    def test_underperform(self):
        """시장 대비 -10% 미만"""
        assert calc_alpha_score(-10.0, 5.0) == 1.0  # alpha = -15%

    def test_missing_returns(self):
        """수익률 데이터 없음"""
        assert calc_alpha_score(None, 5.0) == 2.5
        assert calc_alpha_score(10.0, None) == 2.5


# =============================================================================
# MACD 점수 테스트 (calc_macd_score)
# =============================================================================


class TestMacdScore:
    """MACD 점수 계산 테스트"""

    def test_strong_bullish(self):
        """강한 상승 신호: MACD > 0 and MACD > Signal"""
        assert calc_macd_score(10.0, 5.0) == 5.0

    def test_bullish_crossover(self):
        """상승 전환: MACD < 0 but MACD > Signal"""
        assert calc_macd_score(-5.0, -10.0) == 4.0

    def test_neutral(self):
        """중립: MACD = Signal"""
        assert calc_macd_score(5.0, 5.0) == 3.0

    def test_bearish_crossover(self):
        """하락 전환: MACD > 0 but MACD < Signal"""
        assert calc_macd_score(10.0, 15.0) == 2.0

    def test_strong_bearish(self):
        """강한 하락 신호: MACD < 0 and MACD < Signal"""
        assert calc_macd_score(-10.0, -5.0) == 1.0

    def test_missing_macd(self):
        """MACD 데이터 없음"""
        assert calc_macd_score(None, 5.0) == 2.5
        assert calc_macd_score(5.0, None) == 2.5


# =============================================================================
# ADX 점수 테스트 (calc_adx_score)
# =============================================================================


class TestAdxScore:
    """ADX 점수 계산 테스트"""

    def test_very_strong_trend(self):
        """매우 강한 추세: ADX >= 40"""
        assert calc_adx_score(45.0) == 5.0

    def test_strong_trend(self):
        """강한 추세: 30 <= ADX < 40"""
        assert calc_adx_score(35.0) == 4.0

    def test_moderate_trend(self):
        """보통 추세: 20 <= ADX < 30"""
        assert calc_adx_score(25.0) == 3.0

    def test_weak_trend(self):
        """약한 추세: 15 <= ADX < 20"""
        assert calc_adx_score(17.0) == 2.0

    def test_no_trend(self):
        """추세 없음: ADX < 15"""
        assert calc_adx_score(10.0) == 1.0

    def test_missing_adx(self):
        """ADX 데이터 없음"""
        assert calc_adx_score(None) == 2.5


# =============================================================================
# PBR 점수 테스트 (calc_pbr_score)
# =============================================================================


class TestPbrScore:
    """PBR 점수 계산 테스트"""

    def test_very_undervalued(self):
        """매우 저평가: ratio <= 0.5"""
        assert calc_pbr_score(0.5, 1.0) == 5.0

    def test_undervalued(self):
        """저평가: 0.5 < ratio <= 0.7"""
        assert calc_pbr_score(0.6, 1.0) == 4.0

    def test_fair_value(self):
        """적정: 0.7 < ratio <= 1.0"""
        assert calc_pbr_score(0.9, 1.0) == 3.0

    def test_overvalued(self):
        """고평가: 1.0 < ratio <= 1.3"""
        assert calc_pbr_score(1.2, 1.0) == 2.0

    def test_very_overvalued(self):
        """매우 고평가: ratio > 1.3"""
        assert calc_pbr_score(1.5, 1.0) == 1.0

    def test_negative_pbr(self):
        """자본잠식: PBR < 0"""
        assert calc_pbr_score(-0.5, 1.0) == 0.0

    def test_missing_pbr(self):
        """PBR 데이터 없음"""
        assert calc_pbr_score(None, 1.0) == 2.5

    def test_missing_sector_avg(self):
        """업종 평균 없음 (기본값 1.0 사용)"""
        assert calc_pbr_score(0.5, None) == 5.0


# =============================================================================
# ROE 점수 테스트 (calc_roe_score)
# =============================================================================


class TestRoeScore:
    """ROE 점수 계산 테스트"""

    def test_excellent(self):
        """우수: ROE >= 20%"""
        assert calc_roe_score(25.0) == 5.0

    def test_good(self):
        """양호: 15% <= ROE < 20%"""
        assert calc_roe_score(17.0) == 4.0

    def test_average(self):
        """보통: 10% <= ROE < 15%"""
        assert calc_roe_score(12.0) == 3.0

    def test_below_average(self):
        """미흡: 5% <= ROE < 10%"""
        assert calc_roe_score(7.0) == 2.0

    def test_poor(self):
        """저조: 0% <= ROE < 5%"""
        assert calc_roe_score(3.0) == 1.0

    def test_negative(self):
        """적자: ROE < 0%"""
        assert calc_roe_score(-5.0) == 0.0

    def test_missing_roe(self):
        """ROE 데이터 없음"""
        assert calc_roe_score(None) == 2.5


# =============================================================================
# RubricEngine V2 통합 테스트
# =============================================================================


@dataclass
class MockMarketDataV2:
    """V2 MarketData Mock"""
    symbol: str = "005930"
    name: str = "삼성전자"
    market: str = "KOSPI"
    current_price: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    adx: Optional[float] = None
    foreign_net_buy: Optional[List[float]] = None
    institution_net_buy: Optional[List[float]] = None
    trading_value: Optional[float] = None


@dataclass
class MockFundamentalDataV2:
    """V2 FundamentalData Mock"""
    symbol: str = "005930"
    name: str = "삼성전자"
    per: Optional[float] = None
    sector_avg_per: Optional[float] = None
    pbr: Optional[float] = None
    sector_avg_pbr: Optional[float] = None
    roe: Optional[float] = None
    operating_profit_growth: Optional[float] = None
    debt_ratio: Optional[float] = None


class TestRubricEngineV2:
    """RubricEngine V2 통합 테스트"""

    def test_calculate_with_v2_data(self):
        """V2 모드에서 전체 데이터로 계산"""
        engine = RubricEngine(use_v2=True)

        market_data = MockMarketDataV2(
            current_price=100000,
            ma20=105000,
            ma60=100000,
            rsi=50,
            macd=10.0,
            macd_signal=5.0,
            adx=35.0,
            foreign_net_buy=[100, 50, 30, 20, 10],
            institution_net_buy=[100, 50, 30, 20, 10],
            trading_value=200,
        )

        fundamental_data = MockFundamentalDataV2(
            per=7.5,
            sector_avg_per=15.0,
            pbr=0.8,
            sector_avg_pbr=1.2,
            roe=18.0,
            operating_profit_growth=25.0,
            debt_ratio=50.0,
        )

        result = engine.calculate(
            symbol="005930",
            name="삼성전자",
            market_data=market_data,
            fundamental_data=fundamental_data,
            low_52w=80000,
            high_52w=150000,
            atr_pct=2.5,
            beta=1.0,
            max_drawdown_pct=15.0,
            sector_rank=2,
            sector_total=10,
            stock_return_20d=8.0,
            market_return_20d=5.0,
        )

        # 결과 검증
        assert isinstance(result, RubricResult)
        assert result.rubric_version == "v2"
        assert result.risk is not None
        assert result.relative_strength is not None
        assert result.total_score > 0
        assert result.grade in ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]

        # 6개 카테고리 모두 존재
        assert result.technical is not None
        assert result.supply is not None
        assert result.fundamental is not None
        assert result.market is not None
        assert result.risk is not None
        assert result.relative_strength is not None

    def test_v1_compatibility(self):
        """V1 모드 하위 호환성"""
        engine = RubricEngine(use_v2=False)

        result = engine.calculate(
            symbol="005930",
            name="삼성전자",
        )

        # V1에서는 risk와 relative_strength가 None
        assert result.rubric_version == "v1"
        assert result.risk is None
        assert result.relative_strength is None
        # V1 모드에서는 기존 가중치(100점 만점)가 적용되어 50점이 됨
        # (30+25+25+20 = 100점, 중간값 50% -> 50점)
        assert result.total_score == 50.0

    def test_v2_with_missing_risk_data(self):
        """V2 모드에서 리스크 데이터 없이 계산"""
        engine = RubricEngine(use_v2=True)

        result = engine.calculate(
            symbol="005930",
            name="삼성전자",
        )

        # 리스크 카테고리는 존재하지만 중간값
        assert result.risk is not None
        assert result.risk.score == 50.0  # 중간값
        assert result.relative_strength is not None
        assert result.relative_strength.score == 50.0  # 중간값

    def test_total_score_within_range(self):
        """총점이 0-100 범위 내"""
        engine = RubricEngine(use_v2=True)

        # 최고 점수 시나리오
        result_high = engine.calculate(
            symbol="005930",
            name="삼성전자",
            atr_pct=1.5,
            beta=1.0,
            max_drawdown_pct=8.0,
            sector_rank=1,
            sector_total=10,
            stock_return_20d=15.0,
            market_return_20d=0.0,
        )

        # 최저 점수 시나리오
        result_low = engine.calculate(
            symbol="005930",
            name="삼성전자",
            atr_pct=8.0,
            beta=2.5,
            max_drawdown_pct=40.0,
            sector_rank=10,
            sector_total=10,
            stock_return_20d=-15.0,
            market_return_20d=5.0,
        )

        assert 0 <= result_high.total_score <= 100
        assert 0 <= result_low.total_score <= 100

    def test_extended_technical_details(self):
        """V2에서 기술적 분석에 MACD, ADX 포함"""
        engine = RubricEngine(use_v2=True)

        market_data = MockMarketDataV2(
            ma20=105000,
            ma60=100000,
            rsi=50,
            macd=10.0,
            macd_signal=5.0,
            adx=35.0,
        )

        result = engine.calculate(
            symbol="005930",
            name="삼성전자",
            market_data=market_data,
        )

        # 기술적 분석에 MACD와 ADX 세부 항목 포함
        assert "macd" in result.technical.details
        assert "adx" in result.technical.details

    def test_extended_fundamental_details(self):
        """V2에서 펀더멘털에 PBR, ROE 포함"""
        engine = RubricEngine(use_v2=True)

        fundamental_data = MockFundamentalDataV2(
            per=10.0,
            sector_avg_per=15.0,
            pbr=0.8,
            sector_avg_pbr=1.0,
            roe=15.0,
            operating_profit_growth=20.0,
            debt_ratio=80.0,
        )

        result = engine.calculate(
            symbol="005930",
            name="삼성전자",
            fundamental_data=fundamental_data,
        )

        # 펀더멘털에 PBR과 ROE 세부 항목 포함
        assert "pbr" in result.fundamental.details
        assert "roe" in result.fundamental.details
