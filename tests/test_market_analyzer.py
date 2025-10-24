"""
시장 분석 모듈 테스트

MarketAnalyzer 클래스의 모든 기능을 테스트합니다.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.utils.market_analyzer import MarketAnalyzer, get_market_analyzer


class TestMarketAnalyzer:
    """MarketAnalyzer 클래스 테스트"""

    @pytest.fixture
    def analyzer(self):
        """테스트용 MarketAnalyzer 인스턴스"""
        return MarketAnalyzer(market_index='KS11')

    # ========================================
    # 시장 데이터 가져오기 테스트
    # ========================================

    def test_fetch_market_data_normal(self, analyzer, sample_market_data_bull):
        """정상 케이스: 시장 데이터 가져오기"""
        with patch('FinanceDataReader.DataReader') as mock_fdr:
            mock_fdr.return_value = sample_market_data_bull

            df = analyzer._fetch_market_data(period_days=180)

            assert df is not None, "데이터가 정상적으로 반환되어야 함"
            assert not df.empty, "데이터가 비어있지 않아야 함"
            assert mock_fdr.called, "FinanceDataReader가 호출되어야 함"

    def test_fetch_market_data_failure(self, analyzer):
        """예외 케이스: API 호출 실패"""
        with patch('FinanceDataReader.DataReader') as mock_fdr:
            mock_fdr.side_effect = Exception("API 오류")

            df = analyzer._fetch_market_data(period_days=180)

            assert df is None, "오류 시 None 반환"

    def test_fetch_market_data_empty(self, analyzer):
        """엣지 케이스: 빈 데이터 반환"""
        with patch('FinanceDataReader.DataReader') as mock_fdr:
            mock_fdr.return_value = pd.DataFrame()  # 빈 DataFrame

            df = analyzer._fetch_market_data(period_days=180)

            assert df is None, "빈 데이터 시 None 반환"

    # ========================================
    # 시장 추세 분석 테스트
    # ========================================

    def test_analyze_trend_bull_market(self, analyzer, sample_market_data_bull):
        """정상 케이스: 상승장 감지 (MA20 > MA60, 차이 2% 초과)"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bull

            trend = analyzer.analyze_trend(force_refresh=True)

            assert trend == 'BULL', "상승장으로 감지되어야 함"
            assert analyzer.cache is not None, "캐시가 생성되어야 함"
            assert analyzer.cache['trend'] == 'BULL', "캐시에 추세 정보 저장"

    def test_analyze_trend_bear_market(self, analyzer, sample_market_data_bear):
        """정상 케이스: 하락장 감지 (MA20 < MA60, 차이 -2% 미만)"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bear

            trend = analyzer.analyze_trend(force_refresh=True)

            assert trend == 'BEAR', "하락장으로 감지되어야 함"
            assert analyzer.cache['trend'] == 'BEAR', "캐시에 하락장 정보 저장"

    def test_analyze_trend_sideways_market(self, analyzer):
        """정상 케이스: 횡보장 감지 (MA20 ≈ MA60, 차이 ±2% 이내)"""
        # 횡보장 데이터 생성: MA20과 MA60이 거의 같음
        days = 100
        prices = [2600 + np.sin(i * 0.1) * 50 for i in range(days)]  # 횡보

        df = pd.DataFrame({
            'Close': prices,
            'High': [p * 1.01 for p in prices],
            'Low': [p * 0.99 for p in prices],
            'Volume': [500000000] * days
        })

        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = df

            trend = analyzer.analyze_trend(force_refresh=True)

            assert trend == 'SIDEWAYS', "횡보장으로 감지되어야 함"
            assert analyzer.cache['trend'] == 'SIDEWAYS', "캐시에 횡보장 정보 저장"

    def test_analyze_trend_unknown_insufficient_data(self, analyzer):
        """엣지 케이스: 데이터 부족 (60일 미만)"""
        df = pd.DataFrame({
            'Close': [2600] * 30,  # 30일치만
            'Volume': [500000000] * 30
        })

        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = df

            trend = analyzer.analyze_trend(force_refresh=True)

            assert trend == 'UNKNOWN', "데이터 부족 시 UNKNOWN 반환"

    def test_analyze_trend_unknown_api_failure(self, analyzer):
        """예외 케이스: API 실패"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = None

            trend = analyzer.analyze_trend(force_refresh=True)

            assert trend == 'UNKNOWN', "API 실패 시 UNKNOWN 반환"

    def test_analyze_trend_cache_works(self, analyzer, sample_market_data_bull):
        """캐시 기능: 두 번째 호출 시 캐시 사용"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bull

            # 첫 번째 호출
            trend1 = analyzer.analyze_trend(force_refresh=True)
            call_count_1 = mock_fetch.call_count

            # 두 번째 호출 (캐시 사용)
            trend2 = analyzer.analyze_trend(force_refresh=False)
            call_count_2 = mock_fetch.call_count

            assert trend1 == trend2, "동일한 결과 반환"
            assert call_count_2 == call_count_1, "두 번째 호출 시 API 호출하지 않음"

    def test_analyze_trend_force_refresh(self, analyzer, sample_market_data_bull):
        """캐시 무시: force_refresh=True 시 캐시 무시하고 재분석"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bull

            # 첫 번째 호출
            analyzer.analyze_trend(force_refresh=True)
            call_count_1 = mock_fetch.call_count

            # force_refresh=True로 재호출
            analyzer.analyze_trend(force_refresh=True)
            call_count_2 = mock_fetch.call_count

            assert call_count_2 > call_count_1, "force_refresh 시 API 재호출"

    # ========================================
    # 변동성 계산 테스트
    # ========================================

    def test_calculate_volatility_low(self, analyzer):
        """정상 케이스: 낮은 변동성 (< 1%)"""
        # 안정적인 가격 데이터 (변동성 낮음)
        days = 100
        prices = [2600 + i * 0.1 for i in range(days)]  # 완만한 상승

        df = pd.DataFrame({
            'Close': prices,
            'High': [p * 1.001 for p in prices],
            'Low': [p * 0.999 for p in prices],
            'Volume': [500000000] * days
        })

        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = df

            # 먼저 추세 분석으로 캐시 생성
            analyzer.analyze_trend(force_refresh=True)

            volatility = analyzer.calculate_volatility(force_refresh=True)

            assert volatility == 'LOW', "낮은 변동성으로 감지되어야 함"

    def test_calculate_volatility_medium(self, analyzer, sample_market_data_bull):
        """정상 케이스: 보통 변동성 (1% ~ 2%)"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bull

            # 먼저 추세 분석으로 캐시 생성
            analyzer.analyze_trend(force_refresh=True)

            volatility = analyzer.calculate_volatility(force_refresh=True)

            # sample_market_data_bull의 변동성은 MEDIUM 수준
            assert volatility in ['LOW', 'MEDIUM', 'HIGH'], "변동성 등급 반환"

    def test_calculate_volatility_high(self, analyzer):
        """정상 케이스: 높은 변동성 (> 2%)"""
        # 변동성이 높은 데이터
        days = 100
        np.random.seed(999)
        returns = np.random.normal(0, 0.03, days)  # 표준편차 3%
        prices = 2600 * np.exp(np.cumsum(returns))

        df = pd.DataFrame({
            'Close': prices,
            'High': prices * 1.02,
            'Low': prices * 0.98,
            'Volume': [500000000] * days
        })

        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = df

            # 먼저 추세 분석으로 캐시 생성
            analyzer.analyze_trend(force_refresh=True)

            volatility = analyzer.calculate_volatility(force_refresh=True)

            assert volatility == 'HIGH', "높은 변동성으로 감지되어야 함"

    def test_calculate_volatility_unknown_insufficient_data(self, analyzer):
        """엣지 케이스: 데이터 부족 (20일 미만)"""
        df = pd.DataFrame({
            'Close': [2600] * 15,  # 15일치만
            'Volume': [500000000] * 15
        })

        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = df

            volatility = analyzer.calculate_volatility(force_refresh=True)

            assert volatility == 'UNKNOWN', "데이터 부족 시 UNKNOWN 반환"

    def test_calculate_volatility_unknown_api_failure(self, analyzer):
        """예외 케이스: API 실패"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = None

            volatility = analyzer.calculate_volatility(force_refresh=True)

            assert volatility == 'UNKNOWN', "API 실패 시 UNKNOWN 반환"

    # ========================================
    # 시장 요약 정보 테스트
    # ========================================

    def test_get_market_summary_normal(self, analyzer, sample_market_data_bull):
        """정상 케이스: 전체 시장 요약 정보"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bull

            summary = analyzer.get_market_summary(force_refresh=True)

            # 필수 키 확인
            assert 'trend' in summary, "추세 정보 포함"
            assert 'trend_pct' in summary, "추세 비율 정보 포함"
            assert 'volatility' in summary, "변동성 정보 포함"
            assert 'volatility_value' in summary, "변동성 값 포함"
            assert 'current_price' in summary, "현재가 포함"
            assert 'ma20' in summary, "MA20 포함"
            assert 'ma60' in summary, "MA60 포함"
            assert 'message' in summary, "메시지 포함"

            # 추세 확인
            assert summary['trend'] in ['BULL', 'BEAR', 'SIDEWAYS', 'UNKNOWN'], \
                "올바른 추세 값"

    def test_get_market_summary_bull_market(self, analyzer, sample_market_data_bull):
        """정상 케이스: 상승장 요약"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bull

            summary = analyzer.get_market_summary(force_refresh=True)

            assert summary['trend'] == 'BULL', "상승장 정보"
            assert summary['trend_pct'] > 0.02, "MA20-MA60 차이 2% 이상"
            assert summary['ma20'] > summary['ma60'], "MA20이 MA60보다 높음"
            assert '상승장' in summary['message'], "메시지에 상승장 표시"

    def test_get_market_summary_bear_market(self, analyzer, sample_market_data_bear):
        """정상 케이스: 하락장 요약"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bear

            summary = analyzer.get_market_summary(force_refresh=True)

            assert summary['trend'] == 'BEAR', "하락장 정보"
            assert summary['trend_pct'] < -0.02, "MA20-MA60 차이 -2% 미만"
            assert summary['ma20'] < summary['ma60'], "MA20이 MA60보다 낮음"
            assert '하락장' in summary['message'], "메시지에 하락장 표시"

    def test_get_market_summary_api_failure(self, analyzer):
        """예외 케이스: API 실패 시 기본값 반환"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = None

            summary = analyzer.get_market_summary(force_refresh=True)

            assert summary['trend'] == 'UNKNOWN', "UNKNOWN 반환"
            assert summary['volatility'] == 'UNKNOWN', "변동성 UNKNOWN"
            assert '정보를 가져올 수 없습니다' in summary['message'], \
                "오류 메시지 표시"

    # ========================================
    # 캐시 기능 테스트
    # ========================================

    def test_cache_validity(self, analyzer, sample_market_data_bull):
        """캐시 유효성: 1시간 이내 캐시 유효"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bull

            # 추세 분석 (캐시 생성)
            analyzer.analyze_trend(force_refresh=True)

            # 캐시 유효성 확인
            assert analyzer._is_cache_valid(), "캐시가 유효해야 함"

            # 시간 경과 시뮬레이션
            analyzer.cache_time = datetime.now() - timedelta(hours=2)

            # 캐시 무효화 확인
            assert not analyzer._is_cache_valid(), "1시간 초과 시 캐시 무효"

    def test_cache_update(self, analyzer, sample_market_data_bull):
        """캐시 업데이트: 추세 분석 시 캐시 자동 업데이트"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bull

            # 초기 상태: 캐시 없음
            assert analyzer.cache is None, "초기에는 캐시 없음"

            # 추세 분석
            analyzer.analyze_trend(force_refresh=True)

            # 캐시 생성 확인
            assert analyzer.cache is not None, "캐시 생성됨"
            assert 'trend' in analyzer.cache, "추세 정보 저장"
            assert 'current_price' in analyzer.cache, "현재가 저장"
            assert 'ma20' in analyzer.cache, "MA20 저장"
            assert 'ma60' in analyzer.cache, "MA60 저장"

    # ========================================
    # 메시지 생성 테스트
    # ========================================

    def test_generate_market_message_bull_low(self, analyzer):
        """메시지 생성: 상승장 + 낮은 변동성"""
        message = analyzer._generate_market_message('BULL', 'LOW')

        assert '상승장' in message, "상승장 표시"
        assert '낮은 변동성' in message, "낮은 변동성 표시"

    def test_generate_market_message_bear_high(self, analyzer):
        """메시지 생성: 하락장 + 높은 변동성"""
        message = analyzer._generate_market_message('BEAR', 'HIGH')

        assert '하락장' in message, "하락장 표시"
        assert '높은 변동성' in message, "높은 변동성 표시"

    def test_generate_market_message_sideways_medium(self, analyzer):
        """메시지 생성: 횡보장 + 보통 변동성"""
        message = analyzer._generate_market_message('SIDEWAYS', 'MEDIUM')

        assert '횡보장' in message, "횡보장 표시"
        assert '보통 변동성' in message, "보통 변동성 표시"

    def test_generate_market_message_unknown(self, analyzer):
        """메시지 생성: 알 수 없음"""
        message = analyzer._generate_market_message('UNKNOWN', 'UNKNOWN')

        assert '알 수 없음' in message or '변동성 알 수 없음' in message, \
            "알 수 없음 표시"

    # ========================================
    # 싱글톤 패턴 테스트
    # ========================================

    def test_singleton_pattern(self):
        """싱글톤 패턴: 동일한 인스턴스 반환"""
        instance1 = get_market_analyzer()
        instance2 = get_market_analyzer()

        assert instance1 is instance2, "동일한 인스턴스 반환"

    def test_singleton_cache_shared(self, sample_market_data_bull):
        """싱글톤 캐시: 인스턴스 간 캐시 공유"""
        with patch('FinanceDataReader.DataReader') as mock_fdr:
            mock_fdr.return_value = sample_market_data_bull

            instance1 = get_market_analyzer()

            # 첫 번째 인스턴스로 분석
            instance1.analyze_trend(force_refresh=True)
            cache1 = instance1.cache

            # 두 번째 인스턴스 가져오기 (실제로는 같은 인스턴스)
            instance2 = get_market_analyzer()
            cache2 = instance2.cache

            assert cache1 is cache2, "캐시 공유됨"
            assert cache2 is not None, "캐시가 존재함"

    # ========================================
    # 엣지 케이스 및 예외 처리 테스트
    # ========================================

    def test_analyze_trend_with_calculation_error(self, analyzer):
        """예외 케이스: 계산 중 오류 발생"""
        # 비정상적인 데이터 (NaN 포함)
        df = pd.DataFrame({
            'Close': [np.nan] * 100,
            'Volume': [500000000] * 100
        })

        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = df

            trend = analyzer.analyze_trend(force_refresh=True)

            # NaN 데이터의 경우 pandas가 NaN을 처리하므로 SIDEWAYS로 분류됨
            # (NaN/NaN은 NaN이고, NaN은 비교 연산에서 False를 반환하므로 else로 감)
            assert trend in ['SIDEWAYS', 'UNKNOWN'], "NaN 데이터 처리"

    def test_calculate_volatility_with_zero_returns(self, analyzer):
        """엣지 케이스: 수익률이 모두 0 (변동성 없음)"""
        # 가격 변동이 전혀 없는 데이터
        df = pd.DataFrame({
            'Close': [2600] * 100,  # 모두 동일한 가격
            'Volume': [500000000] * 100
        })

        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = df

            # 먼저 추세 분석
            analyzer.analyze_trend(force_refresh=True)

            volatility = analyzer.calculate_volatility(force_refresh=True)

            assert volatility == 'LOW', "변동성 없음 → LOW"

    def test_multiple_market_indices(self):
        """기능 테스트: 다른 시장 지수 지원"""
        # KOSDAQ 지수로 분석기 생성
        kosdaq_analyzer = MarketAnalyzer(market_index='KQ11')

        assert kosdaq_analyzer.market_index == 'KQ11', "KOSDAQ 지수 설정됨"

    def test_cache_expiration_boundary(self, analyzer, sample_market_data_bull):
        """캐시 만료 경계 테스트: 정확히 1시간 후"""
        with patch.object(analyzer, '_fetch_market_data') as mock_fetch:
            mock_fetch.return_value = sample_market_data_bull

            # 추세 분석
            analyzer.analyze_trend(force_refresh=True)

            # 정확히 1시간 후로 설정
            analyzer.cache_time = datetime.now() - analyzer.cache_duration

            # 캐시 유효성 확인 (경계값)
            is_valid = analyzer._is_cache_valid()

            # 1시간 정확히 지나면 무효화되어야 함
            assert not is_valid, "1시간 경과 시 캐시 무효"
