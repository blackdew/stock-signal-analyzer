"""
Pytest 설정 및 공통 픽스처

이 파일에는 모든 테스트에서 사용할 수 있는 공통 픽스처들이 정의됩니다.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_stock_data():
    """
    샘플 주가 데이터 생성 (180일)

    Returns:
        DataFrame: High, Low, Close, Volume 컬럼을 포함한 주가 데이터
    """
    # 180일 데이터 생성
    days = 180
    base_price = 100000
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # 랜덤 시드 고정 (재현 가능성)
    np.random.seed(42)

    # 가격 시뮬레이션 (랜덤 워크)
    returns = np.random.normal(0.001, 0.02, days)  # 일일 수익률
    prices = base_price * np.exp(np.cumsum(returns))

    # High, Low 생성
    highs = prices * (1 + np.abs(np.random.normal(0, 0.01, days)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.01, days)))
    closes = prices

    # Volume 생성
    base_volume = 1000000
    volumes = base_volume * (1 + np.random.normal(0, 0.3, days))
    volumes = np.maximum(volumes, 0)  # 음수 방지

    df = pd.DataFrame({
        'Date': dates,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes.astype(int)
    })

    df = df.set_index('Date')

    return df


@pytest.fixture
def sample_stock_data_with_trend():
    """
    상승 추세를 가진 샘플 주가 데이터 (180일)

    Returns:
        DataFrame: 상승 추세를 가진 주가 데이터
    """
    days = 180
    base_price = 80000
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    np.random.seed(123)

    # 상승 추세 생성 (평균 수익률 +0.5%)
    returns = np.random.normal(0.005, 0.02, days)
    prices = base_price * np.exp(np.cumsum(returns))

    highs = prices * (1 + np.abs(np.random.normal(0, 0.01, days)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.01, days)))
    closes = prices

    base_volume = 1500000
    volumes = base_volume * (1 + np.random.normal(0, 0.3, days))
    volumes = np.maximum(volumes, 0)

    df = pd.DataFrame({
        'Date': dates,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes.astype(int)
    })

    df = df.set_index('Date')

    return df


@pytest.fixture
def sample_stock_data_volatile():
    """
    변동성이 높은 샘플 주가 데이터 (180일)

    Returns:
        DataFrame: 고변동성 주가 데이터
    """
    days = 180
    base_price = 50000
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    np.random.seed(456)

    # 높은 변동성 (표준편차 5%)
    returns = np.random.normal(0.001, 0.05, days)
    prices = base_price * np.exp(np.cumsum(returns))

    # High, Low 범위도 넓게
    highs = prices * (1 + np.abs(np.random.normal(0, 0.03, days)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.03, days)))
    closes = prices

    base_volume = 2000000
    volumes = base_volume * (1 + np.random.normal(0, 0.5, days))
    volumes = np.maximum(volumes, 0)

    df = pd.DataFrame({
        'Date': dates,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes.astype(int)
    })

    df = df.set_index('Date')

    return df


@pytest.fixture
def sample_insufficient_data():
    """
    데이터가 부족한 경우 (30일)

    Returns:
        DataFrame: 30일치 주가 데이터
    """
    days = 30
    base_price = 120000
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    np.random.seed(789)

    returns = np.random.normal(0.001, 0.02, days)
    prices = base_price * np.exp(np.cumsum(returns))

    highs = prices * (1 + np.abs(np.random.normal(0, 0.01, days)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.01, days)))
    closes = prices

    base_volume = 800000
    volumes = base_volume * (1 + np.random.normal(0, 0.3, days))
    volumes = np.maximum(volumes, 0)

    df = pd.DataFrame({
        'Date': dates,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes.astype(int)
    })

    df = df.set_index('Date')

    return df


@pytest.fixture
def sample_market_data_bull():
    """
    상승장 시장 데이터 (KOSPI 시뮬레이션)

    Returns:
        DataFrame: MA20 > MA60 인 상승장 데이터
    """
    days = 180
    base_price = 2500
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    np.random.seed(100)

    # 강한 상승 추세
    returns = np.random.normal(0.008, 0.015, days)
    prices = base_price * np.exp(np.cumsum(returns))

    highs = prices * (1 + np.abs(np.random.normal(0, 0.005, days)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.005, days)))
    closes = prices

    base_volume = 500000000
    volumes = base_volume * (1 + np.random.normal(0, 0.2, days))
    volumes = np.maximum(volumes, 0)

    df = pd.DataFrame({
        'Date': dates,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes.astype(int)
    })

    df = df.set_index('Date')

    return df


@pytest.fixture
def sample_market_data_bear():
    """
    하락장 시장 데이터 (KOSPI 시뮬레이션)

    Returns:
        DataFrame: MA20 < MA60 인 하락장 데이터
    """
    days = 180
    base_price = 2800
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    np.random.seed(200)

    # 강한 하락 추세
    returns = np.random.normal(-0.006, 0.015, days)
    prices = base_price * np.exp(np.cumsum(returns))

    highs = prices * (1 + np.abs(np.random.normal(0, 0.005, days)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.005, days)))
    closes = prices

    base_volume = 600000000
    volumes = base_volume * (1 + np.random.normal(0, 0.3, days))
    volumes = np.maximum(volumes, 0)

    df = pd.DataFrame({
        'Date': dates,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes.astype(int)
    })

    df = df.set_index('Date')

    return df


@pytest.fixture
def sample_config():
    """
    테스트용 설정 값

    Returns:
        dict: 분석기 설정 딕셔너리
    """
    return {
        'knee_threshold': 0.15,
        'shoulder_threshold': 0.15,
        'stop_loss_pct': 0.07,
        'chase_risk_threshold': 0.25,
        'profit_target_full': 0.30,
        'profit_target_partial': 0.15,
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'lookback_period': 60
    }


@pytest.fixture
def mock_stock_name():
    """
    테스트용 종목명

    Returns:
        str: 샘플 종목명
    """
    return "삼성전자"
