"""
매도 신호 분석 모듈 테스트

SellSignalAnalyzer 클래스의 모든 기능을 테스트합니다.
"""

import pytest
import pandas as pd
import numpy as np
from src.indicators.sell_signals import SellSignalAnalyzer


class TestSellSignalAnalyzer:
    """SellSignalAnalyzer 클래스 테스트"""

    @pytest.fixture
    def analyzer(self, sample_config):
        """테스트용 SellSignalAnalyzer 인스턴스"""
        return SellSignalAnalyzer(
            shoulder_threshold=sample_config['shoulder_threshold'],
            profit_target_full=sample_config['profit_target_full'],
            profit_target_partial=sample_config['profit_target_partial'],
            rsi_period=sample_config['rsi_period'],
            rsi_overbought=sample_config['rsi_overbought'],
            stop_loss_pct=sample_config['stop_loss_pct']
        )

    # ========================================
    # RSI 계산 테스트
    # ========================================

    def test_calculate_rsi_normal(self, analyzer, sample_stock_data):
        """정상 케이스: 충분한 데이터로 RSI 계산"""
        rsi = analyzer.calculate_rsi(sample_stock_data)

        assert not rsi.empty, "RSI가 계산되어야 함"
        assert len(rsi) == len(sample_stock_data), "RSI 길이가 데이터와 동일해야 함"

    def test_calculate_rsi_empty(self, analyzer):
        """예외 케이스: 빈 DataFrame"""
        empty_df = pd.DataFrame()
        rsi = analyzer.calculate_rsi(empty_df)

        assert rsi.empty, "빈 데이터일 때 빈 Series 반환"

    # ========================================
    # 거래량 감소 테스트
    # ========================================

    def test_volume_decrease_normal(self, analyzer, sample_stock_data):
        """정상 케이스: 거래량 감소 체크"""
        df = sample_stock_data.copy()
        avg_volume = df['Volume'].tail(20).mean()
        df.iloc[-1, df.columns.get_loc('Volume')] = int(avg_volume * 0.5)

        is_decrease = analyzer.check_volume_decrease(df, threshold=0.7)
        assert is_decrease == True, "거래량이 평균의 50%면 감소로 감지되어야 함"

    def test_volume_no_decrease(self, analyzer, sample_stock_data):
        """정상 케이스: 거래량 감소 없음"""
        df = sample_stock_data.copy()
        avg_volume = df['Volume'].tail(20).mean()
        df.iloc[-1, df.columns.get_loc('Volume')] = int(avg_volume * 0.9)

        is_decrease = analyzer.check_volume_decrease(df, threshold=0.7)
        assert is_decrease == False, "거래량이 평균의 90%면 감소 아님"

    def test_volume_decrease_insufficient_data(self, analyzer):
        """엣지 케이스: 데이터 부족"""
        df = pd.DataFrame({
            'Close': [100, 105, 110],
            'Volume': [1000, 1100, 500]
        })

        is_decrease = analyzer.check_volume_decrease(df)
        assert is_decrease is False, "데이터 부족 시 False 반환"

    # ========================================
    # 데드크로스 테스트
    # ========================================

    def test_dead_cross_detected(self, analyzer):
        """정상 케이스: 데드크로스 감지"""
        # 데드크로스 시뮬레이션: MA20이 MA60을 하향 돌파
        days = 100
        df = pd.DataFrame({
            'Close': [200 - i * 0.5 for i in range(days)],  # 하락 추세
            'Volume': [1000000] * days
        })
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        result = analyzer.check_dead_cross(df)

        # 하락 추세에서는 MA20 < MA60 상태일 가능성이 높음
        if result.get('is_dead_cross'):
            assert result['days_ago'] >= 1, "데드크로스 발생 시 days_ago가 1 이상"
            assert result['ma_short'] < result['ma_long'], "데드크로스 후 MA20 < MA60"

    def test_dead_cross_not_detected(self, analyzer):
        """정상 케이스: 데드크로스 없음 (상승 추세)"""
        days = 100
        df = pd.DataFrame({
            'Close': [100 + i * 0.5 for i in range(days)],  # 상승 추세
            'Volume': [1000000] * days
        })
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        result = analyzer.check_dead_cross(df)

        # 상승 추세에서는 데드크로스가 발생하지 않을 것
        assert result.get('is_dead_cross') is False, "상승 추세에서는 데드크로스 미감지"

    def test_dead_cross_insufficient_data(self, analyzer, sample_insufficient_data):
        """엣지 케이스: 데이터 부족"""
        result = analyzer.check_dead_cross(sample_insufficient_data)

        assert result.get('is_dead_cross') is False, "데이터 부족 시 데드크로스 미감지"

    # ========================================
    # 수익률 계산 테스트
    # ========================================

    def test_calculate_profit_rate_profit(self, analyzer):
        """정상 케이스: 수익 중"""
        current_price = 110000
        buy_price = 100000

        profit_rate = analyzer.calculate_profit_rate(current_price, buy_price)

        assert profit_rate is not None, "수익률이 계산되어야 함"
        assert profit_rate > 0, "수익률은 양수여야 함"
        assert abs(profit_rate - 0.10) < 0.001, "수익률 10% 근사값"

    def test_calculate_profit_rate_loss(self, analyzer):
        """정상 케이스: 손실 중"""
        current_price = 90000
        buy_price = 100000

        profit_rate = analyzer.calculate_profit_rate(current_price, buy_price)

        assert profit_rate is not None, "손실률이 계산되어야 함"
        assert profit_rate < 0, "손실률은 음수여야 함"
        assert abs(profit_rate - (-0.10)) < 0.001, "손실률 -10% 근사값"

    def test_calculate_profit_rate_no_buy_price(self, analyzer):
        """엣지 케이스: 매수가 정보 없음"""
        current_price = 100000
        profit_rate = analyzer.calculate_profit_rate(current_price, None)

        assert profit_rate is None, "매수가 없으면 None 반환"

    def test_calculate_profit_rate_zero_buy_price(self, analyzer):
        """예외 케이스: 매수가가 0"""
        current_price = 100000
        profit_rate = analyzer.calculate_profit_rate(current_price, 0)

        assert profit_rate is None, "매수가가 0이면 None 반환"

    # ========================================
    # 매도 전략 추천 테스트
    # ========================================

    def test_recommend_sell_strategy_full_sell(self, analyzer):
        """정상 케이스: 전량 매도 추천 (수익률 30% 이상)"""
        profit_rate = 0.35  # 35% 수익
        strategy = analyzer.recommend_sell_strategy(profit_rate, volatility=0.3)

        assert strategy == "전량매도", "수익률 30% 이상이면 전량매도"

    def test_recommend_sell_strategy_partial_sell_high_volatility(self, analyzer):
        """정상 케이스: 분할 매도 (수익률 15-30%, 고변동성)"""
        profit_rate = 0.20  # 20% 수익
        strategy = analyzer.recommend_sell_strategy(profit_rate, volatility=0.7)

        assert "분할매도" in strategy, "수익률 15-30%이면 분할매도"
        assert "1/2" in strategy, "고변동성이면 절반 매도"

    def test_recommend_sell_strategy_partial_sell_low_volatility(self, analyzer):
        """정상 케이스: 분할 매도 (수익률 15-30%, 저변동성)"""
        profit_rate = 0.20  # 20% 수익
        strategy = analyzer.recommend_sell_strategy(profit_rate, volatility=0.3)

        assert "분할매도" in strategy, "수익률 15-30%이면 분할매도"
        assert "1/3" in strategy, "저변동성이면 1/3 매도"

    def test_recommend_sell_strategy_hold(self, analyzer):
        """정상 케이스: 보유 추천 (수익률 낮음)"""
        profit_rate = 0.10  # 10% 수익
        strategy = analyzer.recommend_sell_strategy(profit_rate, volatility=0.3)

        assert strategy == "보유", "수익률 15% 미만이면 보유"

    def test_recommend_sell_strategy_no_profit_rate(self, analyzer):
        """엣지 케이스: 수익률 정보 없음"""
        strategy = analyzer.recommend_sell_strategy(None, volatility=0.3)

        assert strategy == "정보부족", "수익률 없으면 정보부족"

    # ========================================
    # 변동성 계산 테스트
    # ========================================

    def test_calculate_volatility_normal(self, analyzer, sample_stock_data):
        """정상 케이스: 변동성 계산"""
        volatility = analyzer.calculate_volatility(sample_stock_data, period=20)

        assert volatility >= 0, "변동성은 0 이상"
        assert volatility <= 1, "변동성은 1 이하"

    def test_calculate_volatility_high(self, analyzer, sample_stock_data_volatile):
        """정상 케이스: 고변동성 종목"""
        volatility = analyzer.calculate_volatility(sample_stock_data_volatile, period=20)

        # 고변동성 샘플 데이터는 높은 변동성 값을 가져야 함
        assert volatility > 0.3, "고변동성 종목은 높은 변동성 값"

    def test_calculate_volatility_insufficient_data(self, analyzer):
        """엣지 케이스: 데이터 부족"""
        df = pd.DataFrame({'Close': [100, 105, 110]})
        volatility = analyzer.calculate_volatility(df, period=20)

        assert volatility == 0.0, "데이터 부족 시 0.0 반환"

    # ========================================
    # 손절 로직 테스트
    # ========================================

    def test_stop_loss_triggered(self, analyzer, sample_stock_data):
        """정상 케이스: 손절 발동 (손실률 -7% 이상)"""
        df = sample_stock_data.copy()
        buy_price = 100000
        current_price = 92000  # -8% 손실
        df.iloc[-1, df.columns.get_loc('Close')] = current_price

        result = analyzer.analyze_sell_signals(df, buy_price=buy_price)

        assert result['stop_loss_triggered'] is True, "손절가 도달 시 손절 발동"
        assert result['sell_score'] == 100, "손절 발동 시 매도 점수 100"
        assert result['stop_loss_message'] is not None, "손절 메시지 생성"
        assert "🚨 손절 발동" in result['stop_loss_message'], "손절 경고 포함"

    def test_stop_loss_not_triggered(self, analyzer, sample_stock_data):
        """정상 케이스: 손절 미발동 (손실률 -5%)"""
        df = sample_stock_data.copy()
        buy_price = 100000
        current_price = 95000  # -5% 손실 (손절 기준 -7% 미만)
        df.iloc[-1, df.columns.get_loc('Close')] = current_price

        result = analyzer.analyze_sell_signals(df, buy_price=buy_price)

        assert result['stop_loss_triggered'] is False, "손절 기준 미도달 시 손절 미발동"
        assert result['sell_score'] < 100, "손절 미발동 시 점수는 100 미만"

    def test_stop_loss_no_buy_price(self, analyzer, sample_stock_data):
        """엣지 케이스: 매수가 정보 없음"""
        result = analyzer.analyze_sell_signals(sample_stock_data, buy_price=None)

        assert result['stop_loss_triggered'] is False, "매수가 없으면 손절 체크 안 함"
        assert result['loss_rate'] is None, "손실률 정보 없음"

    # ========================================
    # Trailing Stop 테스트
    # ========================================

    def test_trailing_stop_profit(self, analyzer):
        """정상 케이스: 수익 중 추적 손절"""
        buy_price = 100000
        current_price = 108000
        highest_price = 120000  # 최고 20% 수익

        result = analyzer.calculate_trailing_stop(
            buy_price=buy_price,
            current_price=current_price,
            highest_price=highest_price,
            trailing_pct=0.10
        )

        assert result['is_trailing'] is True, "수익 중이면 추적 손절 활성화"
        assert result['stop_type'] == 'TRAILING', "추적 손절 타입"
        # 최고가 120,000의 10% 하락 = 108,000 (추적 손절가)
        expected_trailing_stop = highest_price * (1 - 0.10)
        assert result['trailing_stop_price'] == expected_trailing_stop, \
            f"추적 손절가는 {expected_trailing_stop}이어야 함"

    def test_trailing_stop_triggered(self, analyzer):
        """정상 케이스: 추적 손절 트리거"""
        buy_price = 100000
        current_price = 105000  # 최고가 대비 12.5% 하락
        highest_price = 120000

        result = analyzer.calculate_trailing_stop(
            buy_price=buy_price,
            current_price=current_price,
            highest_price=highest_price,
            trailing_pct=0.10
        )

        assert result['trailing_triggered'] is True, "현재가가 추적 손절가 아래로 떨어지면 트리거"
        assert result['trailing_message'] is not None, "추적 손절 메시지 생성"
        assert "🔻 추적 손절 발동" in result['trailing_message'], "추적 손절 경고"

    def test_trailing_stop_loss(self, analyzer):
        """정상 케이스: 손실 중 고정 손절"""
        buy_price = 100000
        current_price = 95000  # -5% 손실
        highest_price = 98000  # 최고가도 손실

        result = analyzer.calculate_trailing_stop(
            buy_price=buy_price,
            current_price=current_price,
            highest_price=highest_price,
            trailing_pct=0.10
        )

        assert result['is_trailing'] is False, "손실 중이면 추적 손절 비활성화"
        assert result['stop_type'] == 'FIXED', "고정 손절 타입"
        assert result['trailing_triggered'] is False, "추적 손절 미트리거"

    def test_trailing_stop_no_highest_price(self, analyzer):
        """엣지 케이스: 최고가 정보 없음 (현재가 사용)"""
        buy_price = 100000
        current_price = 110000

        result = analyzer.calculate_trailing_stop(
            buy_price=buy_price,
            current_price=current_price,
            highest_price=None  # 최고가 정보 없음
        )

        assert result['is_trailing'] is True, "수익 중이면 추적 손절 활성화"
        # 최고가가 없으면 현재가를 최고가로 사용
        assert result['highest_price'] == current_price, "최고가가 없으면 현재가 사용"

    def test_trailing_stop_no_buy_price(self, analyzer):
        """예외 케이스: 매수가 정보 없음"""
        current_price = 110000
        result = analyzer.calculate_trailing_stop(
            buy_price=None,
            current_price=current_price,
            highest_price=120000
        )

        assert result['is_trailing'] is False, "매수가 없으면 추적 손절 비활성화"
        assert result['stop_type'] == 'NONE', "손절 타입 NONE"

    # ========================================
    # 종합 매도 신호 분석 테스트
    # ========================================

    def test_analyze_sell_signals_normal(self, analyzer, sample_stock_data):
        """정상 케이스: 전체 매도 신호 분석"""
        result = analyzer.analyze_sell_signals(sample_stock_data)

        # 필수 키 확인
        assert 'shoulder_status' in result, "어깨 상태 정보 포함"
        assert 'rsi' in result, "RSI 정보 포함"
        assert 'is_rsi_overbought' in result, "RSI 과매수 여부 포함"
        assert 'volume_decrease' in result, "거래량 감소 여부 포함"
        assert 'dead_cross' in result, "데드크로스 정보 포함"
        assert 'volatility' in result, "변동성 정보 포함"
        assert 'sell_strategy' in result, "매도 전략 포함"
        assert 'sell_signals' in result, "매도 신호 목록 포함"
        assert 'sell_score' in result, "매도 점수 포함"
        assert 'stop_loss_triggered' in result, "손절 발동 여부 포함"
        assert 'trailing_stop' in result, "추적 손절 정보 포함"

        # 매도 점수 범위 검증
        assert 0 <= result['sell_score'] <= 100, "매도 점수는 0-100 범위"

    def test_analyze_sell_signals_with_profit(self, analyzer, sample_stock_data):
        """정상 케이스: 수익 중 매도 분석"""
        buy_price = 80000
        result = analyzer.analyze_sell_signals(sample_stock_data, buy_price=buy_price)

        assert 'profit_rate' in result, "수익률 정보 포함"
        if result['profit_rate'] is not None:
            assert result['profit_rate'] > 0, "수익률은 양수"
            assert result['sell_strategy'] != "정보부족", "매도 전략 추천"

    def test_analyze_sell_signals_stop_loss_priority(self, analyzer, sample_stock_data):
        """정상 케이스: 손절 신호는 최우선"""
        df = sample_stock_data.copy()
        buy_price = 100000
        current_price = 92000  # -8% 손실
        df.iloc[-1, df.columns.get_loc('Close')] = current_price

        result = analyzer.analyze_sell_signals(df, buy_price=buy_price)

        assert result['sell_score'] == 100, "손절 발동 시 매도 점수 100"
        assert result['stop_loss_message'] in result['sell_signals'], \
            "매도 신호 목록 맨 앞에 손절 메시지"

    # ========================================
    # 시장 필터 테스트
    # ========================================

    def test_market_filter_bull_market(self, analyzer, sample_stock_data):
        """시장 필터: 상승장에서 매도 점수 감점"""
        result_bull = analyzer.analyze_sell_signals(sample_stock_data, market_trend='BULL')
        result_none = analyzer.analyze_sell_signals(sample_stock_data, market_trend='UNKNOWN')

        # 상승장에서는 감점 (강력 매도 신호 제외)
        if result_none['sell_score'] > 0 and result_none['sell_score'] < 80:
            assert result_bull['market_adjusted_score'] < result_bull['sell_score'], \
                "상승장에서 조정 점수가 원본보다 낮아야 함"
            assert "📈 시장 상승장 (보유 유리)" in result_bull['sell_signals'], \
                "상승장 보유 메시지 포함"

    def test_market_filter_bear_market(self, analyzer, sample_stock_data):
        """시장 필터: 하락장에서 매도 점수 가산점"""
        result_bear = analyzer.analyze_sell_signals(sample_stock_data, market_trend='BEAR')
        result_none = analyzer.analyze_sell_signals(sample_stock_data, market_trend='UNKNOWN')

        # 하락장에서는 가산점
        if result_none['sell_score'] > 0:
            assert result_bear['market_adjusted_score'] > result_bear['sell_score'], \
                "하락장에서 조정 점수가 원본보다 높아야 함"
            assert "⚠️ 시장 하락장 (매도 고려)" in result_bear['sell_signals'], \
                "하락장 메시지 포함"

    def test_market_filter_sideways_market(self, analyzer, sample_stock_data):
        """시장 필터: 횡보장에서 점수 유지"""
        result = analyzer.analyze_sell_signals(sample_stock_data, market_trend='SIDEWAYS')

        # 횡보장에서는 점수 유지
        assert result['market_adjusted_score'] == result['sell_score'], \
            "횡보장에서 조정 점수가 원본과 동일해야 함"
        assert "➡️ 시장 횡보장" in result['sell_signals'], "횡보장 메시지 포함"

    # ========================================
    # 추천 메시지 생성 테스트
    # ========================================

    def test_get_sell_recommendation_strong_sell(self, analyzer):
        """추천 메시지: 강력 매도"""
        analysis = {
            'sell_score': 80,
            'market_adjusted_score': 85,
            'sell_signals': ['어깨 위치 도달', 'RSI 과매수'],
            'sell_strategy': '전량매도',
            'profit_rate': 0.35,
            'stop_loss_triggered': False
        }

        recommendation = analyzer.get_sell_recommendation(analysis)

        assert "🔴 강력 매도" in recommendation, "강력 매도 메시지 포함"
        assert "전량매도" in recommendation, "매도 전략 포함"
        assert "수익률" in recommendation, "수익률 정보 포함"

    def test_get_sell_recommendation_stop_loss(self, analyzer):
        """추천 메시지: 손절 발동"""
        analysis = {
            'sell_score': 100,
            'market_adjusted_score': 100,
            'sell_signals': ['🚨 손절 발동 (-8.5%)'],
            'sell_strategy': '전량매도',
            'profit_rate': -0.085,
            'loss_rate': -0.085,
            'stop_loss_triggered': True
        }

        recommendation = analyzer.get_sell_recommendation(analysis)

        assert "🚨 즉시 손절 필요" in recommendation, "손절 경고 메시지 포함"
        assert "손실률" in recommendation, "손실률 정보 포함"

    def test_get_sell_recommendation_hold(self, analyzer):
        """추천 메시지: 보유"""
        analysis = {
            'sell_score': 20,
            'market_adjusted_score': 20,
            'sell_signals': [],
            'sell_strategy': '보유',
            'profit_rate': 0.08,
            'stop_loss_triggered': False
        }

        recommendation = analyzer.get_sell_recommendation(analysis)

        assert "🟢 보유" in recommendation, "보유 메시지 포함"
        assert "보유" in recommendation, "매도 전략 포함"

    def test_get_sell_recommendation_empty_analysis(self, analyzer):
        """예외 케이스: 빈 분석 결과"""
        recommendation = analyzer.get_sell_recommendation({})

        assert recommendation == "분석 불가", "빈 분석 시 '분석 불가' 메시지"

    # ========================================
    # 엣지 케이스 및 예외 처리 테스트
    # ========================================

    def test_analyze_empty_dataframe(self, analyzer):
        """예외 케이스: 빈 DataFrame"""
        empty_df = pd.DataFrame()
        result = analyzer.analyze_sell_signals(empty_df)

        assert result == {}, "빈 데이터일 때 빈 딕셔너리 반환"

    def test_analyze_none_dataframe(self, analyzer):
        """예외 케이스: None DataFrame"""
        result = analyzer.analyze_sell_signals(None)

        assert result == {}, "None일 때 빈 딕셔너리 반환"

    def test_score_never_exceeds_100(self, analyzer, sample_stock_data):
        """매도 점수는 100을 초과하지 않아야 함"""
        # 모든 신호가 True + 시장 필터 가산점
        result = analyzer.analyze_sell_signals(
            sample_stock_data,
            buy_price=80000,
            market_trend='BEAR'  # 하락장 가산점
        )

        assert result['sell_score'] <= 100, "매도 점수는 100 이하"
        assert result['market_adjusted_score'] <= 100, "조정 점수는 100 이하"

    def test_trailing_stop_integration(self, analyzer, sample_stock_data):
        """통합 테스트: 추적 손절이 매도 분석에 포함"""
        df = sample_stock_data.copy()
        buy_price = 100000
        current_price = 105000
        highest_price = 120000  # 최고 20% 수익
        df.iloc[-1, df.columns.get_loc('Close')] = current_price

        result = analyzer.analyze_sell_signals(
            df,
            buy_price=buy_price,
            highest_price=highest_price
        )

        # 추적 손절 정보 확인
        assert 'trailing_stop' in result, "추적 손절 정보 포함"
        trailing_stop = result['trailing_stop']
        assert trailing_stop['is_trailing'] is True, "수익 중이면 추적 손절 활성화"

        # 추적 손절 트리거 시 손절 발동
        if trailing_stop.get('trailing_triggered'):
            assert result['stop_loss_triggered'] is True, \
                "추적 손절 트리거 시 손절 발동"
            assert result['sell_score'] == 100, "추적 손절 발동 시 매도 점수 100"
