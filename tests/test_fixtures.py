"""픽스처 테스트

conftest.py의 픽스처들이 제대로 작동하는지 확인합니다.
"""

import pandas as pd


def test_sample_stock_data(sample_stock_data):
    """샘플 주가 데이터 픽스처 테스트"""
    # 데이터가 DataFrame인지 확인
    assert isinstance(sample_stock_data, pd.DataFrame)

    # 필수 컬럼 확인
    required_columns = ['High', 'Low', 'Close', 'Volume']
    for col in required_columns:
        assert col in sample_stock_data.columns

    # 데이터 길이 확인 (180일)
    assert len(sample_stock_data) == 180

    # 가격 데이터가 양수인지 확인
    assert (sample_stock_data['Close'] > 0).all()
    assert (sample_stock_data['High'] > 0).all()
    assert (sample_stock_data['Low'] > 0).all()

    # High >= Low 확인
    assert (sample_stock_data['High'] >= sample_stock_data['Low']).all()


def test_sample_stock_data_with_trend(sample_stock_data_with_trend):
    """상승 추세 데이터 픽스처 테스트"""
    assert isinstance(sample_stock_data_with_trend, pd.DataFrame)
    assert len(sample_stock_data_with_trend) == 180

    # 전반적으로 상승하는지 확인 (첫 가격 < 마지막 가격)
    first_price = sample_stock_data_with_trend['Close'].iloc[0]
    last_price = sample_stock_data_with_trend['Close'].iloc[-1]
    assert last_price > first_price


def test_sample_stock_data_volatile(sample_stock_data_volatile):
    """고변동성 데이터 픽스처 테스트"""
    assert isinstance(sample_stock_data_volatile, pd.DataFrame)
    assert len(sample_stock_data_volatile) == 180

    # 변동성 계산 (일일 수익률의 표준편차)
    returns = sample_stock_data_volatile['Close'].pct_change()
    volatility = returns.std()

    # 고변동성 데이터이므로 변동성이 높아야 함 (3% 이상)
    assert volatility > 0.03


def test_sample_insufficient_data(sample_insufficient_data):
    """데이터 부족 케이스 픽스처 테스트"""
    assert isinstance(sample_insufficient_data, pd.DataFrame)
    assert len(sample_insufficient_data) == 30


def test_sample_market_data_bull(sample_market_data_bull):
    """상승장 시장 데이터 픽스처 테스트"""
    assert isinstance(sample_market_data_bull, pd.DataFrame)
    assert len(sample_market_data_bull) == 180

    # MA20, MA60 계산
    ma20 = sample_market_data_bull['Close'].rolling(20).mean().iloc[-1]
    ma60 = sample_market_data_bull['Close'].rolling(60).mean().iloc[-1]

    # 상승장이므로 MA20 > MA60
    assert ma20 > ma60


def test_sample_market_data_bear(sample_market_data_bear):
    """하락장 시장 데이터 픽스처 테스트"""
    assert isinstance(sample_market_data_bear, pd.DataFrame)
    assert len(sample_market_data_bear) == 180

    # MA20, MA60 계산
    ma20 = sample_market_data_bear['Close'].rolling(20).mean().iloc[-1]
    ma60 = sample_market_data_bear['Close'].rolling(60).mean().iloc[-1]

    # 하락장이므로 MA20 < MA60
    assert ma20 < ma60


def test_sample_config(sample_config):
    """설정 픽스처 테스트"""
    assert isinstance(sample_config, dict)

    # 필수 키 확인
    required_keys = [
        'knee_threshold',
        'shoulder_threshold',
        'stop_loss_pct',
        'rsi_period'
    ]
    for key in required_keys:
        assert key in sample_config
