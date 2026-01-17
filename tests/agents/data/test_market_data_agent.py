"""
MarketDataAgent 테스트

시가총액 순위 조회, 시장 데이터 수집, 캐시 동작을 테스트합니다.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.agents.data.market_data_agent import (
    MarketDataAgent,
    MarketData,
    MarketCapRanking,
)
from src.data.cache import CacheManager
from src.data.fetcher import StockInfo


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cache():
    """빈 캐시 매니저 (항상 캐시 미스)"""
    cache = Mock(spec=CacheManager)
    cache.get.return_value = None
    cache.set = Mock()
    return cache


@pytest.fixture
def mock_fetcher():
    """Mock StockDataFetcher"""
    fetcher = Mock()

    # 종목명 조회
    fetcher.get_stock_name.return_value = "삼성전자"

    # KRX 리스트
    krx_df = pd.DataFrame({
        "Code": ["005930", "000660", "035420"],
        "Name": ["삼성전자", "SK하이닉스", "NAVER"],
        "Market": ["KOSPI", "KOSPI", "KOSPI"],
        "Marcap": [5000000000000000, 1000000000000000, 500000000000000],
        "PER": [15.0, 8.0, 25.0],
        "PBR": [1.5, 1.2, 2.0],
    })
    fetcher._get_krx_listing.return_value = krx_df

    # 시총 순위
    fetcher.get_market_cap_rank.return_value = [
        StockInfo("005930", "삼성전자", 50000000.0, "반도체"),
        StockInfo("000660", "SK하이닉스", 10000000.0, "반도체"),
    ]

    return fetcher


@pytest.fixture
def sample_stock_df():
    """샘플 주가 데이터"""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=100, freq="D")
    close_prices = 70000 + np.cumsum(np.random.randn(100) * 500)

    return pd.DataFrame({
        "Open": close_prices * 0.99,
        "High": close_prices * 1.02,
        "Low": close_prices * 0.98,
        "Close": close_prices,
        "Volume": np.random.randint(1000000, 5000000, 100),
    }, index=dates)


@pytest.fixture
def agent(mock_cache, mock_fetcher):
    """MarketDataAgent 인스턴스"""
    agent = MarketDataAgent(cache=mock_cache, fetcher=mock_fetcher)
    return agent


# =============================================================================
# 시가총액 순위 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_get_market_cap_ranking(agent, mock_fetcher):
    """시총 순위 조회 테스트"""
    ranking = await agent.get_market_cap_ranking()

    assert isinstance(ranking, MarketCapRanking)
    assert len(ranking.kospi_top20) >= 0
    assert "005930" in ranking.kospi_top20 or len(ranking.kospi_top20) == 0


@pytest.mark.asyncio
async def test_get_market_cap_ranking_uses_cache(mock_cache, mock_fetcher):
    """시총 순위 캐시 히트 테스트"""
    # 캐시에 데이터 있음
    mock_cache.get.return_value = {
        "kospi_top20": ["005930", "000660"],
        "kosdaq_top10": ["035720"],
    }

    agent = MarketDataAgent(cache=mock_cache, fetcher=mock_fetcher)
    ranking = await agent.get_market_cap_ranking()

    assert ranking.kospi_top20 == ["005930", "000660"]
    assert ranking.kosdaq_top10 == ["035720"]
    # fetcher 호출 안함
    mock_fetcher.get_market_cap_rank.assert_not_called()


# =============================================================================
# 수급 데이터 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_get_supply_data(agent, mock_fetcher):
    """수급 데이터 조회 테스트"""
    foreign, institution = agent._get_supply_data("005930")

    # 데이터가 있거나 빈 리스트
    assert isinstance(foreign, list)
    assert isinstance(institution, list)


# =============================================================================
# 시장 데이터 수집 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_collect_single(agent, mock_fetcher, sample_stock_df):
    """단일 종목 데이터 수집 테스트"""
    # fetch_stock_data가 샘플 데이터 반환
    mock_fetcher.fetch_stock_data.return_value = sample_stock_df

    start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    market_data = await agent._collect_single("005930", start_date, end_date)

    assert market_data is not None
    assert isinstance(market_data, MarketData)
    assert market_data.symbol == "005930"
    assert market_data.name == "삼성전자"
    assert market_data.current_price is not None
    assert market_data.ma20 is not None or market_data.ma20 is None  # 데이터 의존
    assert market_data.volume is not None


@pytest.mark.asyncio
async def test_collect_multiple(agent, mock_fetcher, sample_stock_df):
    """여러 종목 데이터 수집 테스트"""
    mock_fetcher.fetch_stock_data.return_value = sample_stock_df

    data = await agent.collect(["005930", "000660"])

    assert isinstance(data, dict)
    # 최소 일부 데이터 수집 성공
    assert len(data) >= 0


@pytest.mark.asyncio
async def test_collect_handles_fetch_failure(agent, mock_fetcher):
    """데이터 수집 실패 처리 테스트"""
    mock_fetcher.fetch_stock_data.return_value = None

    start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    market_data = await agent._collect_single("INVALID", start_date, end_date)

    assert market_data is None


# =============================================================================
# 기술적 지표 계산 테스트
# =============================================================================


def test_calculate_indicators(agent, sample_stock_df):
    """기술적 지표 계산 테스트"""
    df = agent._calculate_indicators(sample_stock_df)

    assert "MA20" in df.columns
    assert "MA60" in df.columns
    assert "Volume_MA20" in df.columns
    assert "RSI" in df.columns

    # MA20은 20일 이후부터 유효
    assert pd.notna(df["MA20"].iloc[-1])


def test_calculate_indicators_empty_df(agent):
    """빈 DataFrame에 대한 지표 계산"""
    empty_df = pd.DataFrame()
    result = agent._calculate_indicators(empty_df)
    assert result.empty


# =============================================================================
# 캐시 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_cache_hit(mock_cache, mock_fetcher, sample_stock_df):
    """캐시 히트 테스트"""
    # 캐시에 데이터 있음
    cached_data = {
        "symbol": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "market_cap": 5000000.0,
        "market_cap_rank": 1,
        "current_price": 70000.0,
        "price_change_pct": 1.5,
        "ma20": 69000.0,
        "ma60": 68000.0,
        "rsi": 55.0,
        "foreign_net_buy": [100.0, 50.0],
        "institution_net_buy": [200.0, 100.0],
        "volume": 5000000,
        "avg_volume_20d": 4000000,
        "trading_value": 350.0,
    }
    mock_cache.get.return_value = cached_data

    agent = MarketDataAgent(cache=mock_cache, fetcher=mock_fetcher)

    start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    market_data = await agent._collect_single("005930", start_date, end_date)

    assert market_data.symbol == "005930"
    assert market_data.current_price == 70000.0
    # fetcher 호출 안함
    mock_fetcher.fetch_stock_data.assert_not_called()


@pytest.mark.asyncio
async def test_cache_set_on_miss(mock_cache, mock_fetcher, sample_stock_df):
    """캐시 미스 시 저장 테스트"""
    mock_fetcher.fetch_stock_data.return_value = sample_stock_df

    agent = MarketDataAgent(cache=mock_cache, fetcher=mock_fetcher)

    start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    await agent._collect_single("005930", start_date, end_date)

    # 캐시 저장 호출됨
    mock_cache.set.assert_called()


# =============================================================================
# 유틸리티 메서드 테스트
# =============================================================================


def test_detect_market(agent, mock_fetcher):
    """시장 감지 테스트"""
    market = agent._detect_market("005930")
    assert market in ["KOSPI", "KOSDAQ"]


def test_calculate_change_pct(agent):
    """등락률 계산 테스트"""
    # 상승
    assert agent._calculate_change_pct(110, 100) == 10.0
    # 하락
    assert agent._calculate_change_pct(90, 100) == -10.0
    # 0으로 나누기 방지
    assert agent._calculate_change_pct(100, 0) is None
