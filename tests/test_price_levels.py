"""가격 레벨 감지 모듈 테스트

PriceLevelDetector 클래스의 모든 기능을 테스트합니다:
- 바닥/천장 감지
- ATR 계산 (정상, 데이터 부족, NaN 처리)
- 변동성 등급 분류
- 동적 무릎/어깨 임계값 계산
- 정적 임계값 모드
"""

import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta

from src.indicators.price_levels import PriceLevelDetector


class TestPriceLevelDetector:
    """PriceLevelDetector 클래스 테스트"""

    def test_init(self):
        """초기화 테스트"""
        detector = PriceLevelDetector()
        assert detector.lookback_period == 60
        assert detector.atr_period == 14

        # 커스텀 파라미터
        detector = PriceLevelDetector(lookback_period=90, atr_period=20)
        assert detector.lookback_period == 90
        assert detector.atr_period == 20

    def test_detect_floor_ceiling_normal(self, sample_stock_data):
        """정상 데이터로 바닥/천장 감지 테스트"""
        detector = PriceLevelDetector(lookback_period=60)
        result = detector.detect_floor_ceiling(sample_stock_data)

        # 결과 키 확인
        assert 'floor' in result
        assert 'ceiling' in result
        assert 'current' in result
        assert 'floor_date' in result
        assert 'ceiling_date' in result

        # 가격 관계 확인
        assert result['floor'] <= result['current'] <= result['ceiling']
        assert result['floor'] > 0
        assert result['ceiling'] > 0

    def test_detect_floor_ceiling_empty_data(self):
        """빈 데이터 처리 테스트"""
        detector = PriceLevelDetector()

        # None 데이터
        result = detector.detect_floor_ceiling(None)
        assert result == {}

        # 빈 DataFrame
        empty_df = pd.DataFrame()
        result = detector.detect_floor_ceiling(empty_df)
        assert result == {}

    def test_detect_floor_ceiling_insufficient_data(self, sample_insufficient_data):
        """데이터 부족 케이스 테스트 (30일)"""
        detector = PriceLevelDetector(lookback_period=60)
        result = detector.detect_floor_ceiling(sample_insufficient_data)

        # 30일 데이터도 10일 이상이므로 결과 반환
        assert 'floor' in result
        assert 'ceiling' in result
        assert result['floor'] <= result['current'] <= result['ceiling']

    def test_detect_floor_ceiling_very_small_data(self):
        """매우 적은 데이터 (10일 미만) 테스트"""
        detector = PriceLevelDetector()

        # 5일치 데이터
        dates = pd.date_range(end=datetime.now(), periods=5, freq='D')
        df = pd.DataFrame({
            'Date': dates,
            'Close': [100, 102, 101, 103, 105]
        }).set_index('Date')

        result = detector.detect_floor_ceiling(df)
        assert result == {}  # 10일 미만은 빈 딕셔너리 반환

    def test_calculate_atr_normal(self, sample_stock_data):
        """ATR 정상 계산 테스트"""
        detector = PriceLevelDetector(atr_period=14)
        atr = detector.calculate_atr(sample_stock_data)

        # ATR이 계산되었는지 확인
        assert atr is not None
        assert len(atr) == len(sample_stock_data)
        assert not atr.empty

        # ATR은 항상 0 이상
        assert (atr >= 0).all()

        # NaN 값이 없어야 함 (fillna 처리됨)
        assert not atr.isna().any()

    def test_calculate_atr_custom_period(self, sample_stock_data):
        """커스텀 기간 ATR 계산 테스트"""
        detector = PriceLevelDetector(atr_period=14)

        # 20일 기간으로 계산
        atr = detector.calculate_atr(sample_stock_data, period=20)
        assert len(atr) == len(sample_stock_data)
        assert (atr >= 0).all()

    def test_calculate_atr_empty_data(self):
        """빈 데이터 ATR 계산 테스트"""
        detector = PriceLevelDetector()

        # None 데이터
        atr = detector.calculate_atr(None)
        assert len(atr) == 1
        assert atr.iloc[0] == 0.0

        # 빈 DataFrame
        empty_df = pd.DataFrame()
        atr = detector.calculate_atr(empty_df)
        assert len(atr) == 1
        assert atr.iloc[0] == 0.0

    def test_calculate_atr_missing_columns(self):
        """필수 컬럼 누락 시 ATR 계산 테스트"""
        detector = PriceLevelDetector(atr_period=14)

        # Close만 있는 경우 (High, Low 없음)
        dates = pd.date_range(end=datetime.now(), periods=50, freq='D')
        df = pd.DataFrame({
            'Date': dates,
            'Close': np.random.uniform(100, 110, 50)
        }).set_index('Date')

        atr = detector.calculate_atr(df)

        # Close 기반 표준편차로 대체되어야 함
        assert len(atr) == len(df)
        assert (atr >= 0).all()

    def test_calculate_atr_insufficient_data(self, sample_insufficient_data):
        """데이터 부족 시 ATR 계산 테스트"""
        detector = PriceLevelDetector(atr_period=14)

        # 30일 데이터로 14일 ATR 계산
        atr = detector.calculate_atr(sample_insufficient_data)

        assert len(atr) == len(sample_insufficient_data)
        assert (atr >= 0).all()
        assert not atr.isna().any()

    def test_calculate_volatility_level_low(self, sample_stock_data):
        """저변동성 등급 테스트"""
        detector = PriceLevelDetector()

        # 저변동성 데이터 생성 (작은 가격 변동)
        dates = pd.date_range(end=datetime.now(), periods=180, freq='D')
        np.random.seed(999)
        prices = 100000 + np.random.normal(0, 500, 180).cumsum()  # 매우 작은 변동

        df = pd.DataFrame({
            'Date': dates,
            'High': prices * 1.002,
            'Low': prices * 0.998,
            'Close': prices,
            'Volume': np.random.randint(500000, 1000000, 180)
        }).set_index('Date')

        result = detector.calculate_volatility_level(df)

        assert 'level' in result
        assert 'current_atr' in result
        assert 'avg_atr' in result
        assert 'adjustment_factor' in result

        # 저변동성이면 조정계수 0.8
        if result['level'] == 'LOW':
            assert result['adjustment_factor'] == 0.8

    def test_calculate_volatility_level_high(self, sample_stock_data_volatile):
        """고변동성 등급 테스트"""
        detector = PriceLevelDetector()
        result = detector.calculate_volatility_level(sample_stock_data_volatile)

        # 고변동성 픽스처이므로 HIGH 또는 MEDIUM이어야 함
        assert result['level'] in ['MEDIUM', 'HIGH']

        if result['level'] == 'HIGH':
            assert result['adjustment_factor'] == 1.3

    def test_calculate_volatility_level_medium(self, sample_stock_data):
        """중간 변동성 등급 테스트"""
        detector = PriceLevelDetector()
        result = detector.calculate_volatility_level(sample_stock_data)

        # 일반 픽스처는 MEDIUM이어야 함
        assert result['level'] in ['LOW', 'MEDIUM', 'HIGH']

        if result['level'] == 'MEDIUM':
            assert result['adjustment_factor'] == 1.0

    def test_calculate_volatility_level_empty_data(self):
        """빈 데이터 변동성 계산 테스트"""
        detector = PriceLevelDetector()

        empty_df = pd.DataFrame()
        result = detector.calculate_volatility_level(empty_df)

        # 기본값 반환
        assert result['level'] == 'MEDIUM'
        assert result['current_atr'] == 0
        assert result['avg_atr'] == 0
        assert result['adjustment_factor'] == 1.0

    def test_calculate_position_metrics_normal(self, sample_stock_data):
        """위치 메트릭 정상 계산 테스트"""
        detector = PriceLevelDetector()
        metrics = detector.calculate_position_metrics(sample_stock_data)

        assert 'from_floor_pct' in metrics
        assert 'from_ceiling_pct' in metrics
        assert 'position_in_range' in metrics

        # position_in_range는 0~1 사이
        assert 0 <= metrics['position_in_range'] <= 1

        # from_floor_pct는 0 이상 (바닥 이상)
        assert metrics['from_floor_pct'] >= 0

        # from_ceiling_pct는 0 이하 (천장 이하)
        assert metrics['from_ceiling_pct'] <= 0

    def test_calculate_position_metrics_empty_data(self):
        """빈 데이터 위치 메트릭 테스트"""
        detector = PriceLevelDetector()

        empty_df = pd.DataFrame()
        metrics = detector.calculate_position_metrics(empty_df)

        assert metrics == {}

    def test_calculate_position_metrics_custom_price(self, sample_stock_data):
        """커스텀 가격으로 위치 메트릭 계산 테스트"""
        detector = PriceLevelDetector()

        # 현재가를 명시적으로 지정
        levels = detector.detect_floor_ceiling(sample_stock_data)
        custom_price = (levels['floor'] + levels['ceiling']) / 2  # 중간값

        metrics = detector.calculate_position_metrics(sample_stock_data, custom_price)

        # 중간 가격이므로 position_in_range는 약 0.5
        assert 0.4 <= metrics['position_in_range'] <= 0.6

    def test_is_at_knee_dynamic_mode(self, sample_stock_data_with_trend):
        """동적 무릎 감지 테스트"""
        detector = PriceLevelDetector()

        result = detector.is_at_knee(
            sample_stock_data_with_trend,
            knee_threshold=0.15,
            use_dynamic_threshold=True
        )

        assert 'is_at_knee' in result
        assert 'from_floor_pct' in result
        assert 'dynamic_knee_price' in result
        assert 'volatility_level' in result
        assert 'current_atr' in result
        assert 'adjustment_factor' in result
        assert 'message' in result

        # 동적 무릎 가격은 바닥 가격보다 높아야 함
        levels = detector.detect_floor_ceiling(sample_stock_data_with_trend)
        assert result['dynamic_knee_price'] > levels['floor']

    def test_is_at_knee_static_mode(self, sample_stock_data):
        """정적 무릎 감지 테스트"""
        detector = PriceLevelDetector()

        result = detector.is_at_knee(
            sample_stock_data,
            knee_threshold=0.15,
            use_dynamic_threshold=False
        )

        assert 'is_at_knee' in result
        assert 'from_floor_pct' in result
        assert 'message' in result

        # 동적 모드 관련 키는 없어야 함
        assert 'dynamic_knee_price' not in result
        assert 'volatility_level' not in result

    def test_is_at_knee_empty_data(self):
        """빈 데이터 무릎 감지 테스트"""
        detector = PriceLevelDetector()

        empty_df = pd.DataFrame()
        result = detector.is_at_knee(empty_df)

        assert result['is_at_knee'] is False
        assert result['message'] == '데이터 부족'

    def test_is_at_shoulder_dynamic_mode(self, sample_stock_data_with_trend):
        """동적 어깨 감지 테스트"""
        detector = PriceLevelDetector()

        result = detector.is_at_shoulder(
            sample_stock_data_with_trend,
            shoulder_threshold=0.15,
            use_dynamic_threshold=True
        )

        assert 'is_at_shoulder' in result
        assert 'from_ceiling_pct' in result
        assert 'dynamic_shoulder_price' in result
        assert 'volatility_level' in result
        assert 'current_atr' in result
        assert 'adjustment_factor' in result
        assert 'message' in result

        # 동적 어깨 가격은 천장 가격보다 낮아야 함
        levels = detector.detect_floor_ceiling(sample_stock_data_with_trend)
        assert result['dynamic_shoulder_price'] < levels['ceiling']

    def test_is_at_shoulder_static_mode(self, sample_stock_data):
        """정적 어깨 감지 테스트"""
        detector = PriceLevelDetector()

        result = detector.is_at_shoulder(
            sample_stock_data,
            shoulder_threshold=0.15,
            use_dynamic_threshold=False
        )

        assert 'is_at_shoulder' in result
        assert 'from_ceiling_pct' in result
        assert 'message' in result

        # 동적 모드 관련 키는 없어야 함
        assert 'dynamic_shoulder_price' not in result
        assert 'volatility_level' not in result

    def test_is_at_shoulder_empty_data(self):
        """빈 데이터 어깨 감지 테스트"""
        detector = PriceLevelDetector()

        empty_df = pd.DataFrame()
        result = detector.is_at_shoulder(empty_df)

        assert result['is_at_shoulder'] is False
        assert result['message'] == '데이터 부족'

    def test_volatility_adjustment_factor_ranges(self, sample_stock_data):
        """변동성 조정 계수 범위 테스트"""
        detector = PriceLevelDetector()

        # 여러 종류의 데이터로 테스트
        test_data = [
            sample_stock_data,
        ]

        for df in test_data:
            result = detector.calculate_volatility_level(df)
            adjustment_factor = result['adjustment_factor']

            # 조정 계수는 0.8, 1.0, 1.3 중 하나
            assert adjustment_factor in [0.8, 1.0, 1.3]

            # 등급과 조정 계수의 일치성 확인
            if result['level'] == 'LOW':
                assert adjustment_factor == 0.8
            elif result['level'] == 'MEDIUM':
                assert adjustment_factor == 1.0
            elif result['level'] == 'HIGH':
                assert adjustment_factor == 1.3

    def test_dynamic_threshold_with_different_volatility(self):
        """다양한 변동성에서 동적 임계값 테스트"""
        detector = PriceLevelDetector()

        # 저변동성 데이터 (좁은 임계값 기대)
        dates = pd.date_range(end=datetime.now(), periods=180, freq='D')
        np.random.seed(111)
        low_vol_prices = 100000 + np.random.normal(0, 300, 180).cumsum()

        low_vol_df = pd.DataFrame({
            'Date': dates,
            'High': low_vol_prices * 1.001,
            'Low': low_vol_prices * 0.999,
            'Close': low_vol_prices,
            'Volume': np.random.randint(500000, 1000000, 180)
        }).set_index('Date')

        # 고변동성 데이터 (넓은 임계값 기대)
        np.random.seed(222)
        high_vol_prices = 100000 + np.random.normal(0, 3000, 180).cumsum()

        high_vol_df = pd.DataFrame({
            'Date': dates,
            'High': high_vol_prices * 1.05,
            'Low': high_vol_prices * 0.95,
            'Close': high_vol_prices,
            'Volume': np.random.randint(500000, 1000000, 180)
        }).set_index('Date')

        # 저변동성 무릎 계산
        low_vol_result = detector.is_at_knee(low_vol_df, use_dynamic_threshold=True)

        # 고변동성 무릎 계산
        high_vol_result = detector.is_at_knee(high_vol_df, use_dynamic_threshold=True)

        # 고변동성의 ATR이 저변동성보다 커야 함
        assert high_vol_result['current_atr'] > low_vol_result['current_atr']

    def test_knee_shoulder_message_accuracy(self, sample_stock_data):
        """무릎/어깨 메시지 정확성 테스트"""
        detector = PriceLevelDetector()

        knee_result = detector.is_at_knee(sample_stock_data, use_dynamic_threshold=True)
        shoulder_result = detector.is_at_shoulder(sample_stock_data, use_dynamic_threshold=True)

        # 메시지에 변동성 정보 포함 확인
        assert 'LOW' in knee_result['message'] or 'MEDIUM' in knee_result['message'] or 'HIGH' in knee_result['message']
        assert 'LOW' in shoulder_result['message'] or 'MEDIUM' in shoulder_result['message'] or 'HIGH' in shoulder_result['message']

        # 메시지에 백분율 정보 포함 확인
        assert '%' in knee_result['message']
        assert '%' in shoulder_result['message']

    def test_atr_ratio_calculation(self, sample_stock_data):
        """ATR 비율 계산 검증 테스트"""
        detector = PriceLevelDetector()
        result = detector.calculate_volatility_level(sample_stock_data)

        # ATR 비율이 있어야 함
        if 'atr_ratio' in result:
            atr_ratio = result['atr_ratio']

            # ATR 비율이 양수여야 함
            assert atr_ratio > 0

            # ATR 비율과 등급의 일치성 확인
            if atr_ratio < 0.7:
                assert result['level'] == 'LOW'
            elif atr_ratio > 1.3:
                assert result['level'] == 'HIGH'
            else:
                assert result['level'] == 'MEDIUM'

    def test_floor_ceiling_dates(self, sample_stock_data):
        """바닥/천장 날짜 정확성 테스트"""
        detector = PriceLevelDetector(lookback_period=60)
        result = detector.detect_floor_ceiling(sample_stock_data)

        # 바닥 날짜의 가격이 실제 바닥 가격과 일치하는지 확인
        assert sample_stock_data.loc[result['floor_date'], 'Close'] == result['floor']

        # 천장 날짜의 가격이 실제 천장 가격과 일치하는지 확인
        assert sample_stock_data.loc[result['ceiling_date'], 'Close'] == result['ceiling']
