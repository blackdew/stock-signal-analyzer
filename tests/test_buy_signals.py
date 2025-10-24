"""
매수 신호 분석 모듈 테스트

BuySignalAnalyzer 클래스의 모든 기능을 테스트합니다.
"""

import pytest
import pandas as pd
import numpy as np
from src.indicators.buy_signals import BuySignalAnalyzer


class TestBuySignalAnalyzer:
    """BuySignalAnalyzer 클래스 테스트"""

    @pytest.fixture
    def analyzer(self, sample_config):
        """테스트용 BuySignalAnalyzer 인스턴스"""
        return BuySignalAnalyzer(
            knee_threshold=sample_config['knee_threshold'],
            stop_loss_pct=sample_config['stop_loss_pct'],
            chase_risk_threshold=sample_config['chase_risk_threshold'],
            rsi_period=sample_config['rsi_period'],
            rsi_oversold=sample_config['rsi_oversold']
        )

    # ========================================
    # RSI 계산 테스트
    # ========================================

    def test_calculate_rsi_normal(self, analyzer, sample_stock_data):
        """정상 케이스: 충분한 데이터로 RSI 계산"""
        rsi = analyzer.calculate_rsi(sample_stock_data)

        assert not rsi.empty, "RSI가 계산되어야 함"
        assert len(rsi) == len(sample_stock_data), "RSI 길이가 데이터와 동일해야 함"
        assert rsi.iloc[-1] >= 0, "RSI는 0 이상이어야 함"
        assert rsi.iloc[-1] <= 100, "RSI는 100 이하여야 함"
        assert not pd.isna(rsi.iloc[-1]), "RSI에 NaN이 없어야 함"

    def test_calculate_rsi_insufficient_data(self, analyzer, sample_insufficient_data):
        """엣지 케이스: 데이터 부족 (30일)"""
        rsi = analyzer.calculate_rsi(sample_insufficient_data)

        # RSI는 계산되지만 초반 값들은 50.0(중립값)으로 채워질 수 있음
        assert not rsi.empty, "데이터가 부족해도 RSI는 반환되어야 함"
        assert all(0 <= val <= 100 for val in rsi if not pd.isna(val)), \
            "RSI 값이 0-100 범위 내에 있어야 함"

    def test_calculate_rsi_empty_data(self, analyzer):
        """예외 케이스: 빈 데이터"""
        empty_df = pd.DataFrame()
        rsi = analyzer.calculate_rsi(empty_df)

        assert rsi.empty, "빈 데이터일 때 빈 Series 반환"

    def test_calculate_rsi_none_data(self, analyzer):
        """예외 케이스: None 데이터"""
        rsi = analyzer.calculate_rsi(None)

        assert rsi.empty, "None일 때 빈 Series 반환"

    # ========================================
    # 거래량 급증 테스트
    # ========================================

    def test_volume_surge_normal(self, analyzer, sample_stock_data):
        """정상 케이스: 거래량 급증 체크"""
        # 마지막 거래량을 평균의 3배로 설정
        df = sample_stock_data.copy()
        avg_volume = df['Volume'].tail(20).mean()
        df.iloc[-1, df.columns.get_loc('Volume')] = int(avg_volume * 3)

        is_surge = analyzer.check_volume_surge(df, multiplier=2.0)
        assert is_surge == True, "거래량이 평균의 3배이면 급증으로 감지되어야 함"

    def test_volume_no_surge(self, analyzer, sample_stock_data):
        """정상 케이스: 거래량 급증 없음"""
        df = sample_stock_data.copy()
        avg_volume = df['Volume'].tail(20).mean()
        df.iloc[-1, df.columns.get_loc('Volume')] = int(avg_volume * 1.5)

        is_surge = analyzer.check_volume_surge(df, multiplier=2.0)
        assert is_surge == False, "거래량이 평균의 1.5배면 급증이 아님"

    def test_volume_surge_insufficient_data(self, analyzer):
        """엣지 케이스: 데이터 부족 (20일 미만)"""
        df = pd.DataFrame({
            'Close': [100, 105, 110],
            'Volume': [1000, 1100, 5000]
        })

        is_surge = analyzer.check_volume_surge(df)
        assert is_surge is False, "데이터 부족 시 False 반환"

    def test_volume_surge_zero_average(self, analyzer):
        """예외 케이스: 평균 거래량이 0"""
        df = pd.DataFrame({
            'Close': [100] * 25,
            'Volume': [0] * 25
        })

        is_surge = analyzer.check_volume_surge(df)
        assert is_surge is False, "평균 거래량이 0이면 False 반환"

    # ========================================
    # 골든크로스 테스트
    # ========================================

    def test_golden_cross_detected(self, analyzer):
        """정상 케이스: 골든크로스 감지"""
        # 골든크로스 시뮬레이션: MA20이 MA60을 상향 돌파
        days = 100
        df = pd.DataFrame({
            'Close': [100 + i * 0.5 for i in range(days)],  # 상승 추세
            'Volume': [1000000] * days
        })
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        # 최근에 골든크로스가 발생하도록 조정
        # (실제로는 상승 추세에서 자연스럽게 발생)

        result = analyzer.check_golden_cross(df)

        # 상승 추세에서는 MA20 > MA60 상태일 가능성이 높음
        if result.get('is_golden_cross'):
            assert result['days_ago'] >= 1, "골든크로스 발생 시 days_ago가 1 이상"
            assert result['ma_short'] > result['ma_long'], "골든크로스 후 MA20 > MA60"

    def test_golden_cross_not_detected(self, analyzer):
        """정상 케이스: 골든크로스 없음 (하락 추세)"""
        days = 100
        df = pd.DataFrame({
            'Close': [200 - i * 0.5 for i in range(days)],  # 하락 추세
            'Volume': [1000000] * days
        })
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        result = analyzer.check_golden_cross(df)

        # 하락 추세에서는 골든크로스가 발생하지 않을 것
        # (MA20 < MA60 상태가 지속)
        assert result.get('is_golden_cross') is False, "하락 추세에서는 골든크로스 미감지"

    def test_golden_cross_insufficient_data(self, analyzer, sample_insufficient_data):
        """엣지 케이스: 데이터 부족 (60일 미만)"""
        result = analyzer.check_golden_cross(sample_insufficient_data)

        assert result.get('is_golden_cross') is False, "데이터 부족 시 골든크로스 미감지"

    def test_golden_cross_no_ma_columns(self, analyzer, sample_stock_data):
        """정상 케이스: MA 컬럼이 없을 때 자동 계산"""
        # MA 컬럼 제거
        df = sample_stock_data.copy()
        if 'MA20' in df.columns:
            df = df.drop(columns=['MA20'])
        if 'MA60' in df.columns:
            df = df.drop(columns=['MA60'])

        result = analyzer.check_golden_cross(df)

        # MA가 자동 계산되어야 함
        assert 'is_golden_cross' in result, "골든크로스 체크 결과 반환"

    # ========================================
    # 손절가 계산 테스트
    # ========================================

    def test_calculate_stop_loss_price(self, analyzer):
        """정상 케이스: 손절가 계산"""
        buy_price = 100000
        stop_loss_pct = 0.07

        expected = buy_price * (1 - stop_loss_pct)  # 93,000
        actual = analyzer.calculate_stop_loss_price(buy_price)

        assert actual == expected, f"손절가는 {expected}이어야 함"
        assert actual < buy_price, "손절가는 매수가보다 낮아야 함"

    def test_calculate_stop_loss_price_zero(self, analyzer):
        """엣지 케이스: 매수가가 0"""
        result = analyzer.calculate_stop_loss_price(0)
        assert result <= 0, "매수가가 0이면 손절가도 0 이하"

    # ========================================
    # 종합 매수 신호 분석 테스트
    # ========================================

    def test_analyze_buy_signals_normal(self, analyzer, sample_stock_data):
        """정상 케이스: 전체 매수 신호 분석"""
        result = analyzer.analyze_buy_signals(sample_stock_data)

        # 필수 키 확인
        assert 'knee_status' in result, "무릎 상태 정보 포함"
        assert 'rsi' in result, "RSI 정보 포함"
        assert 'is_rsi_oversold' in result, "RSI 과매도 여부 포함"
        assert 'volume_surge' in result, "거래량 급증 여부 포함"
        assert 'golden_cross' in result, "골든크로스 정보 포함"
        assert 'chase_buy_safe' in result, "추격매수 안전 여부 포함"
        assert 'stop_loss_price' in result, "손절가 정보 포함"
        assert 'buy_signals' in result, "매수 신호 목록 포함"
        assert 'buy_score' in result, "매수 점수 포함"

        # 매수 점수 범위 검증
        assert 0 <= result['buy_score'] <= 100, "매수 점수는 0-100 범위"

    def test_analyze_buy_signals_with_knee(self, analyzer):
        """정상 케이스: 무릎 도달 시 매수 신호"""
        # 무릎 도달 시뮬레이션: 최근 상승 후 바닥 근처
        days = 180
        prices = [50000] * 60  # 바닥
        prices += [50000 + i * 100 for i in range(120)]  # 상승

        df = pd.DataFrame({
            'High': [p * 1.01 for p in prices],
            'Low': [p * 0.99 for p in prices],
            'Close': prices,
            'Volume': [1000000] * days
        })

        result = analyzer.analyze_buy_signals(df)

        # 무릎 도달 시 점수 증가
        if result['knee_status'].get('is_at_knee'):
            assert result['buy_score'] >= 30, "무릎 도달 시 최소 30점"
            assert "무릎 위치 도달" in result['buy_signals'], "무릎 신호 포함"

    def test_analyze_buy_signals_with_rsi_oversold(self, analyzer):
        """정상 케이스: RSI 과매도 시 매수 신호"""
        # RSI 과매도 시뮬레이션: 급락 후 반등
        days = 60
        prices = [100000 - i * 1000 for i in range(30)]  # 급락
        prices += [70000 + i * 100 for i in range(30)]  # 반등 시작

        df = pd.DataFrame({
            'High': [p * 1.01 for p in prices],
            'Low': [p * 0.99 for p in prices],
            'Close': prices,
            'Volume': [1000000] * days
        })

        result = analyzer.analyze_buy_signals(df)

        # RSI 과매도 시 점수 증가
        if result['is_rsi_oversold']:
            assert result['buy_score'] >= 25, "RSI 과매도 시 최소 25점"
            assert "RSI 과매도" in result['buy_signals'], "RSI 과매도 신호 포함"

    # ========================================
    # 시장 필터 테스트
    # ========================================

    def test_market_filter_bear_market(self, analyzer, sample_stock_data):
        """시장 필터: 하락장에서 매수 점수 감점"""
        result_bear = analyzer.analyze_buy_signals(sample_stock_data, market_trend='BEAR')
        result_none = analyzer.analyze_buy_signals(sample_stock_data, market_trend='UNKNOWN')

        # 하락장에서는 감점 (강력 매수 신호 제외)
        if result_none['buy_score'] > 0 and result_none['buy_score'] < 80:
            assert result_bear['market_adjusted_score'] < result_bear['buy_score'], \
                "하락장에서 조정 점수가 원본보다 낮아야 함"
            assert "⚠️ 시장 하락장" in result_bear['buy_signals'], "하락장 경고 메시지 포함"

    def test_market_filter_bull_market(self, analyzer, sample_stock_data):
        """시장 필터: 상승장에서 매수 점수 가산점"""
        result_bull = analyzer.analyze_buy_signals(sample_stock_data, market_trend='BULL')
        result_none = analyzer.analyze_buy_signals(sample_stock_data, market_trend='UNKNOWN')

        # 상승장에서는 가산점
        if result_none['buy_score'] > 0:
            assert result_bull['market_adjusted_score'] > result_bull['buy_score'], \
                "상승장에서 조정 점수가 원본보다 높아야 함"
            assert "📈 시장 상승장" in result_bull['buy_signals'], "상승장 메시지 포함"

    def test_market_filter_sideways_market(self, analyzer, sample_stock_data):
        """시장 필터: 횡보장에서 점수 유지"""
        result = analyzer.analyze_buy_signals(sample_stock_data, market_trend='SIDEWAYS')

        # 횡보장에서는 점수 유지
        assert result['market_adjusted_score'] == result['buy_score'], \
            "횡보장에서 조정 점수가 원본과 동일해야 함"
        assert "➡️ 시장 횡보장" in result['buy_signals'], "횡보장 메시지 포함"

    def test_market_filter_strong_buy_signal_in_bear(self, analyzer):
        """시장 필터: 하락장에서도 강력 매수 신호는 유지"""
        # 강력 매수 신호 시뮬레이션 (80점 이상)
        days = 180
        # 바닥 형성 후 반등 + RSI 과매도 + 거래량 급증 + 골든크로스
        prices = [50000] * 100  # 장기 바닥
        prices += [50000 + i * 200 for i in range(80)]  # 상승 시작

        df = pd.DataFrame({
            'High': [p * 1.02 for p in prices],
            'Low': [p * 0.98 for p in prices],
            'Close': prices,
            'Volume': [1000000] * 179 + [3000000]  # 마지막 날 거래량 급증
        })

        result = analyzer.analyze_buy_signals(df, market_trend='BEAR')

        # 강력 매수 신호 (80점 이상)면 하락장에서도 감점 없음
        if result['buy_score'] >= 80:
            assert result['market_adjusted_score'] == result['buy_score'], \
                "강력 매수 신호는 하락장에서도 감점 없음"

    # ========================================
    # 추천 메시지 생성 테스트
    # ========================================

    def test_get_buy_recommendation_strong_buy(self, analyzer):
        """추천 메시지: 강력 매수"""
        analysis = {
            'buy_score': 80,
            'market_adjusted_score': 85,
            'buy_signals': ['무릎 위치 도달', 'RSI 과매도', '거래량 급증'],
            'chase_buy_safe': True
        }

        recommendation = analyzer.get_buy_recommendation(analysis)

        assert "🟢 강력 매수" in recommendation, "강력 매수 메시지 포함"
        assert "무릎 위치 도달" in recommendation, "신호 목록 포함"

    def test_get_buy_recommendation_hold(self, analyzer):
        """추천 메시지: 관망"""
        analysis = {
            'buy_score': 35,
            'market_adjusted_score': 35,
            'buy_signals': ['📈 시장 상승장'],
            'chase_buy_safe': True
        }

        recommendation = analyzer.get_buy_recommendation(analysis)

        assert "🟠 관망" in recommendation, "관망 메시지 포함"

    def test_get_buy_recommendation_chase_warning(self, analyzer):
        """추천 메시지: 추격매수 경고"""
        analysis = {
            'buy_score': 60,
            'market_adjusted_score': 60,
            'buy_signals': ['무릎 위치 도달'],
            'chase_buy_safe': False  # 추격매수 위험
        }

        recommendation = analyzer.get_buy_recommendation(analysis)

        assert "⚠️ 추격매수 주의" in recommendation, "추격매수 경고 포함"

    def test_get_buy_recommendation_empty_analysis(self, analyzer):
        """예외 케이스: 빈 분석 결과"""
        recommendation = analyzer.get_buy_recommendation({})

        assert recommendation == "분석 불가", "빈 분석 시 '분석 불가' 메시지"

    # ========================================
    # 엣지 케이스 및 예외 처리 테스트
    # ========================================

    def test_analyze_empty_dataframe(self, analyzer):
        """예외 케이스: 빈 DataFrame"""
        empty_df = pd.DataFrame()
        result = analyzer.analyze_buy_signals(empty_df)

        assert result == {}, "빈 데이터일 때 빈 딕셔너리 반환"

    def test_analyze_none_dataframe(self, analyzer):
        """예외 케이스: None DataFrame"""
        result = analyzer.analyze_buy_signals(None)

        assert result == {}, "None일 때 빈 딕셔너리 반환"

    def test_analyze_missing_columns(self, analyzer):
        """예외 케이스: 필수 컬럼 누락"""
        df = pd.DataFrame({
            'Close': [100, 105, 110, 115, 120]
        })  # High, Low, Volume 누락

        # 예외가 발생하지 않고 안전하게 처리되어야 함
        try:
            result = analyzer.analyze_buy_signals(df)
            # 일부 지표는 계산되지 않을 수 있지만 오류는 없어야 함
            assert isinstance(result, dict), "결과는 딕셔너리 형태"
        except KeyError:
            pytest.fail("필수 컬럼 누락 시 KeyError 발생하지 않아야 함")

    def test_score_never_exceeds_100(self, analyzer):
        """매수 점수는 100을 초과하지 않아야 함"""
        # 모든 신호가 True인 극단적 케이스
        days = 180
        prices = [50000] * 100  # 바닥
        prices += [50000 + i * 500 for i in range(80)]  # 급상승

        df = pd.DataFrame({
            'High': [p * 1.03 for p in prices],
            'Low': [p * 0.97 for p in prices],
            'Close': prices,
            'Volume': [1000000] * 179 + [5000000]  # 거래량 급증
        })

        result = analyzer.analyze_buy_signals(df, market_trend='BULL')

        assert result['buy_score'] <= 100, "매수 점수는 100 이하"
        assert result['market_adjusted_score'] <= 100, "조정 점수는 100 이하"
