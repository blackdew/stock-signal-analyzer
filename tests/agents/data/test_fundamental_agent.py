"""
FundamentalAgent 테스트

PER, PBR, ROE, 부채비율 조회 및 섹터 평균 계산을 테스트합니다.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

from src.agents.data.fundamental_agent import (
    FundamentalAgent,
    FundamentalData,
)
from src.data.cache import CacheManager


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
        "Code": ["005930", "000660", "035420", "042700", "010140", "009540", "042660"],
        "Name": ["삼성전자", "SK하이닉스", "NAVER", "한미반도체", "삼성중공업", "한국조선해양", "대우조선해양"],
        "Market": ["KOSPI", "KOSPI", "KOSPI", "KOSDAQ", "KOSPI", "KOSPI", "KOSPI"],
        "Marcap": [5000000000000000, 1000000000000000, 500000000000000,
                   100000000000000, 200000000000000, 150000000000000, 100000000000000],
        "PER": [15.0, 8.0, 25.0, 20.0, 12.0, 10.0, 8.0],
        "PBR": [1.5, 1.2, 2.0, 3.0, 0.8, 0.7, 0.6],
    })
    fetcher._get_krx_listing.return_value = krx_df

    return fetcher


@pytest.fixture
def agent(mock_cache, mock_fetcher):
    """FundamentalAgent 인스턴스"""
    agent = FundamentalAgent(cache=mock_cache, fetcher=mock_fetcher)
    return agent


# =============================================================================
# 기본 데이터 조회 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_collect_single(agent, mock_fetcher):
    """단일 종목 재무 데이터 수집 테스트"""
    data = await agent._collect_single("005930")

    assert data is not None
    assert isinstance(data, FundamentalData)
    assert data.symbol == "005930"
    assert data.name == "삼성전자"
    # PER, PBR은 KRX 데이터에서 가져옴
    assert data.per == 15.0
    assert data.pbr == 1.5


@pytest.mark.asyncio
async def test_collect_multiple(agent, mock_fetcher):
    """여러 종목 재무 데이터 수집 테스트"""
    data = await agent.collect(["005930", "000660"])

    assert isinstance(data, dict)
    assert len(data) == 2
    assert "005930" in data
    assert "000660" in data
    assert data["005930"].per == 15.0
    assert data["000660"].per == 8.0


@pytest.mark.asyncio
async def test_collect_handles_unknown_symbol(agent, mock_fetcher):
    """알 수 없는 종목 처리 테스트"""
    # KRX 리스트에 없는 종목
    data = await agent._collect_single("999999")

    # 기본 정보만 반환
    assert data is not None
    assert data.symbol == "999999"
    assert data.per is None
    assert data.pbr is None


# =============================================================================
# 섹터 평균 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_calculate_sector_averages(agent, mock_fetcher):
    """섹터 평균 계산 테스트"""
    await agent._calculate_sector_averages()

    # 반도체 섹터 평균 (005930, 000660, 042700)
    assert "반도체" in agent._sector_averages_cache
    semi_avg = agent._sector_averages_cache["반도체"]
    # PER: (15 + 8 + 20) / 3 = 14.33
    # PBR: (1.5 + 1.2 + 3.0) / 3 = 1.9
    assert semi_avg["per"] is not None
    assert semi_avg["pbr"] is not None


@pytest.mark.asyncio
async def test_get_sector_average(agent, mock_fetcher):
    """섹터 평균 조회 테스트"""
    await agent._calculate_sector_averages()

    avg = agent.get_sector_average("반도체")
    assert "per" in avg
    assert "pbr" in avg


def test_get_sector_average_unknown(agent):
    """존재하지 않는 섹터 평균 조회"""
    avg = agent.get_sector_average("unknown_sector")
    assert avg["per"] is None
    assert avg["pbr"] is None


# =============================================================================
# 캐시 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_cache_hit(mock_cache, mock_fetcher):
    """캐시 히트 테스트"""
    cached_data = {
        "symbol": "005930",
        "name": "삼성전자",
        "sector": "반도체",
        "per": 15.0,
        "pbr": 1.5,
        "roe": 10.0,
        "operating_margin": 15.0,
        "revenue_growth": 5.0,
        "operating_profit_growth": 8.0,
        "debt_ratio": 30.0,
        "sector_avg_per": 14.0,
        "sector_avg_pbr": 1.8,
    }
    mock_cache.get.return_value = cached_data

    agent = FundamentalAgent(cache=mock_cache, fetcher=mock_fetcher)
    data = await agent._collect_single("005930")

    assert data.per == 15.0
    assert data.roe == 10.0
    # fetcher 호출 안함 (종목명 제외)
    mock_fetcher._get_krx_listing.assert_not_called()


@pytest.mark.asyncio
async def test_cache_set_on_miss(mock_cache, mock_fetcher):
    """캐시 미스 시 저장 테스트"""
    agent = FundamentalAgent(cache=mock_cache, fetcher=mock_fetcher)
    await agent._collect_single("005930")

    # 캐시 저장 호출됨
    mock_cache.set.assert_called()


# =============================================================================
# 재무 데이터 가져오기 테스트
# =============================================================================


def test_fetch_financial_data(agent, mock_fetcher):
    """재무 데이터 가져오기 테스트"""
    data = agent._fetch_financial_data("005930")

    # KRX 데이터에서 PER, PBR 가져옴
    assert data.get("per") == 15.0
    assert data.get("pbr") == 1.5


def test_fetch_financial_data_negative_values(agent, mock_fetcher):
    """음수 PER/PBR 제외 테스트"""
    # KRX 리스트에 음수 값 추가
    krx_df = pd.DataFrame({
        "Code": ["123456"],
        "Name": ["테스트종목"],
        "PER": [-5.0],  # 음수 PER
        "PBR": [-1.0],  # 음수 PBR
    })
    mock_fetcher._get_krx_listing.return_value = krx_df

    data = agent._fetch_financial_data("123456")

    # 음수는 제외됨
    assert "per" not in data
    assert "pbr" not in data


# =============================================================================
# FundamentalData 구조 테스트
# =============================================================================


def test_fundamental_data_defaults():
    """FundamentalData 기본값 테스트"""
    data = FundamentalData(symbol="005930", name="삼성전자")

    assert data.symbol == "005930"
    assert data.name == "삼성전자"
    assert data.sector is None
    assert data.per is None
    assert data.pbr is None
    assert data.roe is None
    assert data.operating_margin is None
    assert data.revenue_growth is None
    assert data.operating_profit_growth is None
    assert data.debt_ratio is None
    assert data.sector_avg_per is None
    assert data.sector_avg_pbr is None


def test_fundamental_data_with_values():
    """FundamentalData 값 설정 테스트"""
    data = FundamentalData(
        symbol="005930",
        name="삼성전자",
        sector="반도체",
        per=15.0,
        pbr=1.5,
        roe=10.0,
        debt_ratio=30.0,
    )

    assert data.per == 15.0
    assert data.pbr == 1.5
    assert data.roe == 10.0
    assert data.debt_ratio == 30.0
