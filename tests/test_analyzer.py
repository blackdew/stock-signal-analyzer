"""통합 테스트: StockAnalyzer 전체 파이프라인 테스트"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.analysis.analyzer import StockAnalyzer


class TestStockAnalyzer:
    """StockAnalyzer 통합 테스트"""

    def test_init(self):
        """StockAnalyzer 초기화 테스트"""
        analyzer = StockAnalyzer(
            knee_threshold=0.15,
            shoulder_threshold=0.15,
            stop_loss_pct=0.07,
            rsi_period=14,
            lookback_period=60
        )

        assert analyzer is not None
        assert analyzer.fetcher is not None
        assert analyzer.price_detector is not None
        assert analyzer.buy_analyzer is not None
        assert analyzer.sell_analyzer is not None
        assert analyzer.market_analyzer is not None


    def test_analyze_stock_success(self, sample_stock_data, mock_stock_name):
        """정상적인 종목 분석 테스트"""
        analyzer = StockAnalyzer()

        # FinanceDataReader 모킹
        with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=sample_stock_data):
            with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                    # 시장 분석 모킹 (캐시된 데이터 사용)
                    with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='BULL'):
                        with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                            mock_summary.return_value = {
                                'trend': 'BULL',
                                'ma20': 2650.0,
                                'ma60': 2500.0,
                                'trend_diff': 0.06,
                                'volatility': 'MEDIUM'
                            }

                            result = analyzer.analyze_stock(
                                symbol='005930',
                                start_date='2024-01-01',
                                end_date='2024-06-30',
                                buy_price=70000
                            )

        # 결과 검증
        assert result is not None
        assert 'error' not in result
        assert result['symbol'] == '005930'
        assert result['name'] == mock_stock_name
        assert result['current_price'] > 0
        assert 'price_levels' in result
        assert 'volatility_info' in result
        assert 'knee_info' in result
        assert 'shoulder_info' in result
        assert 'market_summary' in result
        assert 'buy_analysis' in result
        assert 'sell_analysis' in result
        assert 'overall_recommendation' in result
        assert 'action' in result
        assert result['action'] in ['BUY', 'SELL', 'HOLD']


    def test_analyze_stock_api_failure(self):
        """API 호출 실패 시 에러 처리 테스트"""
        analyzer = StockAnalyzer()

        # API 실패 모킹 (None 반환)
        with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=None):
            result = analyzer.analyze_stock(
                symbol='999999',
                start_date='2024-01-01',
                end_date='2024-06-30'
            )

        # 에러 처리 검증
        assert result is not None
        assert 'error' in result
        assert result['symbol'] == '999999'
        assert '데이터를 가져올 수 없습니다' in result['error']


    def test_analyze_stock_empty_data(self):
        """빈 데이터 처리 테스트"""
        analyzer = StockAnalyzer()

        # 빈 DataFrame 모킹
        empty_df = pd.DataFrame()
        with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=empty_df):
            result = analyzer.analyze_stock(
                symbol='000000',
                start_date='2024-01-01',
                end_date='2024-06-30'
            )

        # 에러 처리 검증
        assert result is not None
        assert 'error' in result
        assert result['symbol'] == '000000'


    def test_analyze_stock_with_buy_price(self, sample_stock_data, mock_stock_name):
        """매수가 포함 분석 테스트 (수익률 계산)"""
        analyzer = StockAnalyzer()

        with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=sample_stock_data):
            with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                    with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='SIDEWAYS'):
                        with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                            mock_summary.return_value = {
                                'trend': 'SIDEWAYS',
                                'ma20': 2600.0,
                                'ma60': 2600.0,
                                'trend_diff': 0.0,
                                'volatility': 'MEDIUM'
                            }

                            result = analyzer.analyze_stock(
                                symbol='005930',
                                start_date='2024-01-01',
                                end_date='2024-06-30',
                                buy_price=70000
                            )

        # 매수가 정보가 매도 분석에 반영되었는지 확인
        assert 'sell_analysis' in result
        sell_analysis = result['sell_analysis']
        # 수익률 또는 손절 정보가 있어야 함
        assert 'profit_rate' in sell_analysis or 'stop_loss_triggered' in sell_analysis


    def test_analyze_stock_with_highest_price(self, sample_stock_data, mock_stock_name):
        """최고가 포함 분석 테스트 (Trailing Stop)"""
        analyzer = StockAnalyzer()

        with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=sample_stock_data):
            with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                    with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='BULL'):
                        with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                            mock_summary.return_value = {
                                'trend': 'BULL',
                                'ma20': 2650.0,
                                'ma60': 2500.0,
                                'trend_diff': 0.06,
                                'volatility': 'LOW'
                            }

                            result = analyzer.analyze_stock(
                                symbol='005930',
                                start_date='2024-01-01',
                                end_date='2024-06-30',
                                buy_price=70000,
                                highest_price=80000  # 최고가 전달
                            )

        # Trailing Stop 정보가 매도 분석에 반영되었는지 확인
        assert 'sell_analysis' in result
        sell_analysis = result['sell_analysis']
        # Trailing stop 정보가 있어야 함 (trailing_stop 딕셔너리)
        assert 'trailing_stop' in sell_analysis
        trailing_stop = sell_analysis['trailing_stop']
        # trailing_stop 딕셔너리에 필요한 키들이 있어야 함
        assert 'trailing_stop_price' in trailing_stop or 'is_trailing' in trailing_stop


    def test_analyze_multiple_stocks_success(self, sample_stock_data, mock_stock_name):
        """여러 종목 동시 분석 성공 테스트"""
        analyzer = StockAnalyzer()
        symbols = ['005930', '000660', '035420']

        with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=sample_stock_data):
            with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                    with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='BULL'):
                        with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                            mock_summary.return_value = {
                                'trend': 'BULL',
                                'ma20': 2650.0,
                                'ma60': 2500.0,
                                'trend_diff': 0.06,
                                'volatility': 'MEDIUM'
                            }

                            results = analyzer.analyze_multiple_stocks(
                                symbols=symbols,
                                start_date='2024-01-01',
                                end_date='2024-06-30'
                            )

        # 결과 검증
        assert len(results) == 3
        for result in results:
            assert 'error' not in result
            assert result['symbol'] in symbols
            assert 'action' in result


    def test_analyze_multiple_stocks_with_buy_prices(self, sample_stock_data, mock_stock_name):
        """매수가 딕셔너리 포함 여러 종목 분석 테스트"""
        analyzer = StockAnalyzer()
        symbols = ['005930', '000660']
        buy_prices = {'005930': 70000, '000660': 120000}

        with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=sample_stock_data):
            with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                    with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='SIDEWAYS'):
                        with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                            mock_summary.return_value = {
                                'trend': 'SIDEWAYS',
                                'ma20': 2600.0,
                                'ma60': 2600.0,
                                'trend_diff': 0.0,
                                'volatility': 'MEDIUM'
                            }

                            results = analyzer.analyze_multiple_stocks(
                                symbols=symbols,
                                start_date='2024-01-01',
                                end_date='2024-06-30',
                                buy_prices=buy_prices
                            )

        # 결과 검증
        assert len(results) == 2
        for result in results:
            assert 'sell_analysis' in result
            # 수익률 정보가 있어야 함
            sell_analysis = result['sell_analysis']
            assert 'profit_rate' in sell_analysis or 'stop_loss_triggered' in sell_analysis


    def test_analyze_multiple_stocks_with_highest_prices(self, sample_stock_data, mock_stock_name):
        """최고가 딕셔너리 포함 여러 종목 분석 테스트"""
        analyzer = StockAnalyzer()
        symbols = ['005930', '000660']
        buy_prices = {'005930': 70000, '000660': 120000}
        highest_prices = {'005930': 80000, '000660': 130000}

        with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=sample_stock_data):
            with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                    with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='BULL'):
                        with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                            mock_summary.return_value = {
                                'trend': 'BULL',
                                'ma20': 2650.0,
                                'ma60': 2500.0,
                                'trend_diff': 0.06,
                                'volatility': 'LOW'
                            }

                            results = analyzer.analyze_multiple_stocks(
                                symbols=symbols,
                                start_date='2024-01-01',
                                end_date='2024-06-30',
                                buy_prices=buy_prices,
                                highest_prices=highest_prices
                            )

        # 결과 검증
        assert len(results) == 2
        for result in results:
            assert 'sell_analysis' in result
            sell_analysis = result['sell_analysis']
            # Trailing stop 정보가 있어야 함 (trailing_stop 딕셔너리)
            assert 'trailing_stop' in sell_analysis
            trailing_stop = sell_analysis['trailing_stop']
            # trailing_stop 딕셔너리에 필요한 키들이 있어야 함
            assert 'trailing_stop_price' in trailing_stop or 'is_trailing' in trailing_stop


    def test_analyze_multiple_stocks_partial_failure(self, sample_stock_data, mock_stock_name):
        """일부 종목 실패 시 나머지 계속 진행 테스트"""
        analyzer = StockAnalyzer()
        symbols = ['005930', '999999', '000660']  # 999999는 실패할 것

        def mock_fetch(symbol, start, end):
            if symbol == '999999':
                return None  # 실패
            return sample_stock_data

        with patch.object(analyzer.fetcher, 'fetch_stock_data', side_effect=mock_fetch):
            with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                    with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='SIDEWAYS'):
                        with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                            mock_summary.return_value = {
                                'trend': 'SIDEWAYS',
                                'ma20': 2600.0,
                                'ma60': 2600.0,
                                'trend_diff': 0.0,
                                'volatility': 'MEDIUM'
                            }

                            results = analyzer.analyze_multiple_stocks(
                                symbols=symbols,
                                start_date='2024-01-01',
                                end_date='2024-06-30'
                            )

        # 결과 검증
        assert len(results) == 3
        # 999999는 에러, 나머지는 성공
        success_count = sum(1 for r in results if 'error' not in r)
        error_count = sum(1 for r in results if 'error' in r)
        assert success_count == 2
        assert error_count == 1


    def test_get_priority_stocks_buy(self, sample_stock_data, mock_stock_name):
        """매수 우선순위 종목 추출 테스트"""
        analyzer = StockAnalyzer()
        symbols = ['005930', '000660', '035420']

        # 각 종목별로 다른 매수 점수를 반환하도록 모킹
        mock_results = []
        for i, symbol in enumerate(symbols):
            mock_result = {
                'symbol': symbol,
                'name': f'종목{i}',
                'current_price': 70000 + i * 1000,
                'buy_analysis': {
                    'buy_score': 80 - i * 10,  # 80, 70, 60
                    'market_adjusted_score': 85 - i * 10  # 85, 75, 65
                },
                'sell_analysis': {
                    'sell_score': 20,
                    'market_adjusted_score': 20
                },
                'action': 'BUY'
            }
            mock_results.append(mock_result)

        # 우선순위 추출
        priority_stocks = analyzer.get_priority_stocks(mock_results, action='BUY', top_n=2)

        # 검증
        assert len(priority_stocks) == 2
        # 점수 순서대로 정렬되었는지 확인
        assert priority_stocks[0]['symbol'] == '005930'  # 85점
        assert priority_stocks[1]['symbol'] == '000660'  # 75점


    def test_get_priority_stocks_sell(self, sample_stock_data, mock_stock_name):
        """매도 우선순위 종목 추출 테스트"""
        analyzer = StockAnalyzer()
        symbols = ['005930', '000660', '035420']

        # 각 종목별로 다른 매도 점수를 반환하도록 모킹
        mock_results = []
        for i, symbol in enumerate(symbols):
            mock_result = {
                'symbol': symbol,
                'name': f'종목{i}',
                'current_price': 70000 + i * 1000,
                'buy_analysis': {
                    'buy_score': 20,
                    'market_adjusted_score': 20
                },
                'sell_analysis': {
                    'sell_score': 60 + i * 10,  # 60, 70, 80
                    'market_adjusted_score': 65 + i * 10  # 65, 75, 85
                },
                'action': 'SELL'
            }
            mock_results.append(mock_result)

        # 우선순위 추출
        priority_stocks = analyzer.get_priority_stocks(mock_results, action='SELL', top_n=2)

        # 검증
        assert len(priority_stocks) == 2
        # 점수 순서대로 정렬되었는지 확인 (높은 순)
        assert priority_stocks[0]['symbol'] == '035420'  # 85점
        assert priority_stocks[1]['symbol'] == '000660'  # 75점


    def test_get_priority_stocks_with_errors(self):
        """에러가 있는 종목 제외 테스트"""
        analyzer = StockAnalyzer()

        mock_results = [
            {
                'symbol': '005930',
                'buy_analysis': {'buy_score': 80, 'market_adjusted_score': 80},
                'sell_analysis': {'sell_score': 20, 'market_adjusted_score': 20}
            },
            {
                'symbol': '999999',
                'error': '데이터 없음'
            },
            {
                'symbol': '000660',
                'buy_analysis': {'buy_score': 70, 'market_adjusted_score': 70},
                'sell_analysis': {'sell_score': 20, 'market_adjusted_score': 20}
            }
        ]

        # 우선순위 추출
        priority_stocks = analyzer.get_priority_stocks(mock_results, action='BUY', top_n=5)

        # 에러가 있는 종목(999999) 제외되었는지 확인
        assert len(priority_stocks) == 2
        assert all(r['symbol'] != '999999' for r in priority_stocks)


    def test_action_decision_buy_priority(self, sample_stock_data, mock_stock_name):
        """액션 결정: 매수 우선 (임계값 + 점수 차이 조건 충족)"""
        analyzer = StockAnalyzer()

        # 매수 점수가 높고 매도 점수보다 충분히 우위인 경우
        with patch.object(analyzer.buy_analyzer, 'analyze_buy_signals') as mock_buy:
            with patch.object(analyzer.sell_analyzer, 'analyze_sell_signals') as mock_sell:
                with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=sample_stock_data):
                    with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                        with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                            with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='BULL'):
                                with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                                    mock_summary.return_value = {
                                        'trend': 'BULL',
                                        'ma20': 2650.0,
                                        'ma60': 2500.0,
                                        'trend_diff': 0.06,
                                        'volatility': 'MEDIUM'
                                    }

                                    # 매수 점수 50, 매도 점수 20 (차이 30 > 임계값 10)
                                    mock_buy.return_value = {
                                        'buy_score': 50,
                                        'market_adjusted_score': 50,
                                        'signals': []
                                    }
                                    mock_sell.return_value = {
                                        'sell_score': 20,
                                        'market_adjusted_score': 20,
                                        'signals': []
                                    }

                                    result = analyzer.analyze_stock(
                                        symbol='005930',
                                        start_date='2024-01-01',
                                        end_date='2024-06-30'
                                    )

        # BUY 액션 확인
        assert result['action'] == 'BUY'


    def test_action_decision_sell_priority(self, sample_stock_data, mock_stock_name):
        """액션 결정: 매도 우선 (임계값 + 점수 차이 조건 충족)"""
        analyzer = StockAnalyzer()

        # 매도 점수가 높고 매수 점수보다 충분히 우위인 경우
        with patch.object(analyzer.buy_analyzer, 'analyze_buy_signals') as mock_buy:
            with patch.object(analyzer.sell_analyzer, 'analyze_sell_signals') as mock_sell:
                with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=sample_stock_data):
                    with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                        with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                            with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='BEAR'):
                                with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                                    mock_summary.return_value = {
                                        'trend': 'BEAR',
                                        'ma20': 2500.0,
                                        'ma60': 2650.0,
                                        'trend_diff': -0.06,
                                        'volatility': 'HIGH'
                                    }

                                    # 매수 점수 20, 매도 점수 50 (차이 30 > 임계값 10)
                                    mock_buy.return_value = {
                                        'buy_score': 20,
                                        'market_adjusted_score': 20,
                                        'signals': []
                                    }
                                    mock_sell.return_value = {
                                        'sell_score': 50,
                                        'market_adjusted_score': 50,
                                        'signals': []
                                    }

                                    result = analyzer.analyze_stock(
                                        symbol='005930',
                                        start_date='2024-01-01',
                                        end_date='2024-06-30',
                                        buy_price=70000
                                    )

        # SELL 액션 확인
        assert result['action'] == 'SELL'


    def test_action_decision_hold_low_scores(self, sample_stock_data, mock_stock_name):
        """액션 결정: 관망 (점수가 모두 낮음)"""
        analyzer = StockAnalyzer()

        # 매수/매도 점수가 모두 임계값 미만
        with patch.object(analyzer.buy_analyzer, 'analyze_buy_signals') as mock_buy:
            with patch.object(analyzer.sell_analyzer, 'analyze_sell_signals') as mock_sell:
                with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=sample_stock_data):
                    with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                        with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                            with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='SIDEWAYS'):
                                with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                                    mock_summary.return_value = {
                                        'trend': 'SIDEWAYS',
                                        'ma20': 2600.0,
                                        'ma60': 2600.0,
                                        'trend_diff': 0.0,
                                        'volatility': 'MEDIUM'
                                    }

                                    # 매수 점수 25, 매도 점수 20 (둘 다 임계값 30 미만)
                                    mock_buy.return_value = {
                                        'buy_score': 25,
                                        'market_adjusted_score': 25,
                                        'signals': []
                                    }
                                    mock_sell.return_value = {
                                        'sell_score': 20,
                                        'market_adjusted_score': 20,
                                        'signals': []
                                    }

                                    result = analyzer.analyze_stock(
                                        symbol='005930',
                                        start_date='2024-01-01',
                                        end_date='2024-06-30'
                                    )

        # HOLD 액션 확인
        assert result['action'] == 'HOLD'


    def test_action_decision_hold_small_diff(self, sample_stock_data, mock_stock_name):
        """액션 결정: 관망 (점수 차이가 작음)"""
        analyzer = StockAnalyzer()

        # 점수는 높지만 차이가 임계값(10) 미만
        with patch.object(analyzer.buy_analyzer, 'analyze_buy_signals') as mock_buy:
            with patch.object(analyzer.sell_analyzer, 'analyze_sell_signals') as mock_sell:
                with patch.object(analyzer.fetcher, 'fetch_stock_data', return_value=sample_stock_data):
                    with patch.object(analyzer.fetcher, 'get_stock_name', return_value=mock_stock_name):
                        with patch.object(analyzer.fetcher, 'calculate_technical_indicators', return_value=sample_stock_data):
                            with patch.object(analyzer.market_analyzer, 'analyze_trend', return_value='SIDEWAYS'):
                                with patch.object(analyzer.market_analyzer, 'get_market_summary') as mock_summary:
                                    mock_summary.return_value = {
                                        'trend': 'SIDEWAYS',
                                        'ma20': 2600.0,
                                        'ma60': 2600.0,
                                        'trend_diff': 0.0,
                                        'volatility': 'MEDIUM'
                                    }

                                    # 매수 점수 45, 매도 점수 40 (차이 5 < 임계값 10)
                                    mock_buy.return_value = {
                                        'buy_score': 45,
                                        'market_adjusted_score': 45,
                                        'signals': []
                                    }
                                    mock_sell.return_value = {
                                        'sell_score': 40,
                                        'market_adjusted_score': 40,
                                        'signals': []
                                    }

                                    result = analyzer.analyze_stock(
                                        symbol='005930',
                                        start_date='2024-01-01',
                                        end_date='2024-06-30'
                                    )

        # HOLD 액션 확인 (점수 차이가 작아서)
        assert result['action'] == 'HOLD'
