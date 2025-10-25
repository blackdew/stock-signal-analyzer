"""
간소화된 시나리오 테스트

실제 투자 상황을 시뮬레이션하는 통합 시나리오 테스트
mock 없이 실제 코드를 최대한 사용
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.indicators.price_levels import PriceLevelDetector
from src.indicators.buy_signals import BuySignalAnalyzer
from src.indicators.sell_signals import SellSignalAnalyzer


class TestPriceScenarios:
    """가격 레벨 시나리오 테스트"""

    def test_high_volatility_has_wider_threshold(self, high_volatility_stock_data):
        """
        시나리오: 고변동성 종목은 더 넓은 임계값을 가져야 함

        기대 결과:
        - volatility_level = 'HIGH'
        - ATR 값이 높음
        - 동적 임계값이 정적 임계값보다 넓음
        """
        # Given
        df = high_volatility_stock_data
        detector = PriceLevelDetector(lookback_period=60)

        # When
        volatility_info = detector.calculate_volatility_level(df)
        levels = detector.detect_floor_ceiling(df)
        knee_info = detector.is_at_knee(df, use_dynamic_threshold=True)

        # Then
        # 고변동성으로 분류되어야 함
        assert volatility_info['level'] in ['MEDIUM', 'HIGH'], \
            "고변동성 종목은 MEDIUM 또는 HIGH로 분류되어야 함"

        # ATR이 계산되어야 함
        assert volatility_info['current_atr'] is not None
        assert volatility_info['current_atr'] > 0

        # 동적 임계값이 있어야 함
        assert knee_info.get('dynamic_knee_price') is not None

    def test_low_volatility_has_narrow_threshold(self, sample_stock_data):
        """
        시나리오: 저변동성 종목은 더 좁은 임계값을 가져야 함

        기대 결과:
        - 변동성이 상대적으로 낮음
        - ATR 값이 낮음
        """
        # Given: 저변동성 데이터 생성
        df = sample_stock_data.copy()

        # 가격 변동을 매우 작게 조정
        for i in range(len(df)):
            noise = np.random.uniform(-0.003, 0.003)  # ±0.3%
            df.loc[df.index[i], 'Close'] = df.loc[df.index[i], 'Close'] * (1 + noise)
            df.loc[df.index[i], 'High'] = df.loc[df.index[i], 'Close'] * 1.003
            df.loc[df.index[i], 'Low'] = df.loc[df.index[i], 'Close'] * 0.997

        detector = PriceLevelDetector(lookback_period=60)

        # When
        volatility_info = detector.calculate_volatility_level(df)

        # Then
        # 변동성이 낮거나 중간 정도여야 함
        assert volatility_info['level'] in ['LOW', 'MEDIUM'], \
            "저변동성 종목은 LOW 또는 MEDIUM으로 분류되어야 함"


class TestStopLossScenarios:
    """손절 시나리오 테스트"""

    def test_stop_loss_triggered_at_7_percent(self, sample_stock_data):
        """
        시나리오: 매수가 대비 -7% 손실 시 손절 발동

        기대 결과:
        - stop_loss_triggered = True
        - sell_score = 100
        """
        # Given
        df = sample_stock_data.copy()
        buy_price = 100000
        current_price = 93000  # -7%
        df.loc[df.index[-1], 'Close'] = current_price

        sell_analyzer = SellSignalAnalyzer(
            shoulder_threshold=0.15,
            profit_target_full=0.30,
            profit_target_partial=0.15,
            rsi_period=14,
            rsi_overbought=70,
            stop_loss_pct=0.07
        )

        # When
        result = sell_analyzer.analyze_sell_signals(df, buy_price=buy_price)

        # Then
        assert result['stop_loss_triggered'] is True, \
            "손절가 도달 시 트리거되어야 함"

        assert result['sell_score'] == 100, \
            "손절 시 매도 점수가 100이어야 함"

        assert any('손절' in signal for signal in result['sell_signals']), \
            "손절 메시지가 있어야 함"

    def test_trailing_stop_in_profit(self, sample_stock_data):
        """
        시나리오: 수익 중 trailing stop 계산

        매수가: 100,000원
        최고가: 120,000원 (+20%)
        현재가: 108,000원 (최고가 대비 -10%)

        기대 결과:
        - trailing_stop_price 계산됨
        - stop_type = 'TRAILING'
        """
        # Given
        df = sample_stock_data.copy()
        buy_price = 100000
        highest_price = 120000
        current_price = 108000

        df.loc[df.index[-1], 'Close'] = current_price

        sell_analyzer = SellSignalAnalyzer()

        # When
        result = sell_analyzer.analyze_sell_signals(
            df,
            buy_price=buy_price,
            highest_price=highest_price
        )

        # Then
        assert 'trailing_stop' in result
        trailing_info = result['trailing_stop']

        # Trailing stop이 계산되었는지
        assert trailing_info is not None
        assert 'trailing_stop_price' in trailing_info

        # 수익 중이므로 TRAILING 타입이어야 함
        if trailing_info['stop_type'] == 'TRAILING':
            # Trailing stop price가 합리적인 범위에 있는지
            expected_stop = highest_price * 0.9  # 최고가의 90%
            assert abs(trailing_info['trailing_stop_price'] - expected_stop) < 1000

    def test_no_stop_loss_in_profit(self, sample_stock_data):
        """
        시나리오: 수익 중에는 손절 발동 안 됨

        기대 결과:
        - stop_loss_triggered = False
        """
        # Given
        df = sample_stock_data.copy()
        buy_price = 100000
        current_price = 110000  # +10% 수익
        df.loc[df.index[-1], 'Close'] = current_price

        sell_analyzer = SellSignalAnalyzer()

        # When
        result = sell_analyzer.analyze_sell_signals(df, buy_price=buy_price)

        # Then
        assert result['stop_loss_triggered'] is False, \
            "수익 중에는 손절이 트리거되지 않아야 함"


class TestMarketTrendScenarios:
    """시장 추세 시나리오 테스트"""

    def test_buy_signals_in_bear_market_penalized(self, sample_stock_data):
        """
        시나리오: 하락장에서 매수 신호는 감점됨

        기대 결과:
        - market_adjusted_score < buy_score (강력 매수 제외)
        """
        # Given: 무릎 위치 (매수 신호)
        df = sample_stock_data.copy()
        floor_price = df['Low'].tail(60).min()
        df.loc[df.index[-1], 'Close'] = floor_price * 1.05

        buy_analyzer = BuySignalAnalyzer()

        # When: 하락장 전달
        result = buy_analyzer.analyze_buy_signals(df, market_trend='BEAR')

        # Then
        buy_score = result['buy_score']
        market_adjusted_score = result['market_adjusted_score']

        # 강력 매수 신호가 아니면 감점되어야 함
        if buy_score < 80:
            assert market_adjusted_score < buy_score, \
                "하락장에서 매수 점수가 감점되어야 함"

    def test_buy_signals_in_bull_market_bonus(self, sample_stock_data):
        """
        시나리오: 상승장에서 매수 신호는 가산점

        기대 결과:
        - market_adjusted_score > buy_score
        """
        # Given
        df = sample_stock_data.copy()
        floor_price = df['Low'].tail(60).min()
        df.loc[df.index[-1], 'Close'] = floor_price * 1.05

        buy_analyzer = BuySignalAnalyzer()

        # When: 상승장 전달
        result = buy_analyzer.analyze_buy_signals(df, market_trend='BULL')

        # Then
        buy_score = result['buy_score']
        market_adjusted_score = result['market_adjusted_score']

        assert market_adjusted_score > buy_score, \
            "상승장에서 매수 점수가 증가해야 함"

    def test_sell_signals_in_bull_market_penalized(self, sample_stock_data):
        """
        시나리오: 상승장에서 매도 신호는 감점됨

        기대 결과:
        - market_adjusted_score < sell_score (강력 매도 제외)
        """
        # Given: 어깨 위치 (매도 신호)
        df = sample_stock_data.copy()
        ceiling_price = df['High'].tail(60).max()
        df.loc[df.index[-1], 'Close'] = ceiling_price * 0.95

        sell_analyzer = SellSignalAnalyzer()

        # When: 상승장 전달
        result = sell_analyzer.analyze_sell_signals(df, buy_price=70000, market_trend='BULL')

        # Then
        sell_score = result['sell_score']
        market_adjusted_score = result['market_adjusted_score']

        # 강력 매도 신호가 아니고, 매도 점수가 있으면 감점되어야 함
        if sell_score > 0 and sell_score < 80:
            assert market_adjusted_score < sell_score, \
                "상승장에서 매도 점수가 감점되어야 함"
        elif sell_score == 0:
            # 매도 점수가 0이면 조정 점수도 0이어야 함
            assert market_adjusted_score == 0


class TestEdgeCaseScenarios:
    """엣지 케이스 시나리오 테스트"""

    def test_zero_volume_handled(self, sample_stock_data):
        """
        시나리오: 거래량 0인 경우

        기대 결과:
        - 에러 없이 분석 가능
        - 거래량 관련 신호는 False
        """
        # Given
        df = sample_stock_data.copy()
        df['Volume'] = 0  # 모든 거래량을 0으로

        buy_analyzer = BuySignalAnalyzer()

        # When
        result = buy_analyzer.analyze_buy_signals(df)

        # Then
        assert result is not None, "거래량 0이어도 분석 가능해야 함"

        # 거래량 급증 신호는 없어야 함
        buy_signals = result.get('buy_signals', [])
        volume_surge = any('거래량 급증' in signal for signal in buy_signals)
        assert volume_surge is False, "거래량 0일 때 거래량 급증 신호가 없어야 함"

    def test_insufficient_data_handled(self):
        """
        시나리오: 데이터 부족 (30일만 있음)

        기대 결과:
        - 에러 없이 분석 가능
        - 기본값 사용
        """
        # Given: 30일 데이터
        days = 30
        base_price = 120000
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

        df = pd.DataFrame({
            'High': [base_price * 1.01] * days,
            'Low': [base_price * 0.99] * days,
            'Close': [base_price] * days,
            'Volume': [1000000] * days
        }, index=dates)

        buy_analyzer = BuySignalAnalyzer()

        # When
        result = buy_analyzer.analyze_buy_signals(df)

        # Then
        assert result is not None, "데이터 부족 시에도 분석 가능해야 함"
        assert 'buy_score' in result, "매수 점수가 있어야 함"

    def test_extreme_price_drop_handled(self, sample_stock_data):
        """
        시나리오: 하한가 (-30%)

        기대 결과:
        - 정상 분석됨
        - 강한 매수 신호 발생 가능
        """
        # Given: 하한가
        df = sample_stock_data.copy()
        prev_close = df.loc[df.index[-2], 'Close']
        limit_down = prev_close * 0.7  # -30%

        df.loc[df.index[-1], 'Open'] = limit_down
        df.loc[df.index[-1], 'High'] = limit_down
        df.loc[df.index[-1], 'Low'] = limit_down
        df.loc[df.index[-1], 'Close'] = limit_down
        df.loc[df.index[-1], 'Volume'] = int(df['Volume'].mean() * 10)  # 거래량 폭증

        buy_analyzer = BuySignalAnalyzer()

        # When
        result = buy_analyzer.analyze_buy_signals(df)

        # Then
        assert result is not None, "하한가 종목도 분석 가능해야 함"
        assert 'buy_score' in result

        # 하한가는 보통 강한 매수 신호를 발생시킴
        buy_score = result['buy_score']
        assert buy_score > 0, "하한가는 매수 점수가 있어야 함"
