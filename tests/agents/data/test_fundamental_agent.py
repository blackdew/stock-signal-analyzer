"""
FundamentalAgent 테스트

PER, PBR, ROE, 부채비율 조회 및 섹터 평균 계산을 테스트합니다.
네이버 금융 크롤링 기반으로 동작합니다.
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
    fetcher.get_stock_name.return_value = "삼성전자"
    return fetcher


@pytest.fixture
def agent(mock_cache, mock_fetcher):
    """FundamentalAgent 인스턴스"""
    agent = FundamentalAgent(cache=mock_cache, fetcher=mock_fetcher)
    return agent


# =============================================================================
# Mock 네이버 금융 데이터
# =============================================================================

MOCK_NAVER_DATA = {
    "005930": {
        "per": 15.0,
        "pbr": 1.5,
        "roe": 10.0,
        "operating_margin": 15.0,
        "operating_profit_growth": 8.0,
        "debt_ratio": 30.0,
    },
    "000660": {
        "per": 8.0,
        "pbr": 1.2,
        "roe": 15.0,
        "operating_margin": 20.0,
        "operating_profit_growth": 12.0,
        "debt_ratio": 25.0,
    },
}


# =============================================================================
# 기본 데이터 조회 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_collect_single(agent, mock_fetcher):
    """단일 종목 재무 데이터 수집 테스트"""
    # _fetch_from_naver 메서드 모킹
    with patch.object(agent, '_fetch_from_naver', return_value=MOCK_NAVER_DATA["005930"]):
        data = await agent._collect_single("005930")

    assert data is not None
    assert isinstance(data, FundamentalData)
    assert data.symbol == "005930"
    assert data.name == "삼성전자"
    # 네이버 금융에서 가져온 데이터
    assert data.per == 15.0
    assert data.pbr == 1.5
    assert data.roe == 10.0
    assert data.operating_margin == 15.0
    assert data.debt_ratio == 30.0


@pytest.mark.asyncio
async def test_collect_multiple(agent, mock_fetcher):
    """여러 종목 재무 데이터 수집 테스트"""
    def mock_fetch_from_naver(symbol):
        return MOCK_NAVER_DATA.get(symbol, {})

    with patch.object(agent, '_fetch_from_naver', side_effect=mock_fetch_from_naver):
        mock_fetcher.get_stock_name.side_effect = lambda s: "삼성전자" if s == "005930" else "SK하이닉스"
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
    # 네이버에서 데이터를 가져오지 못하는 경우
    with patch.object(agent, '_fetch_from_naver', return_value={}):
        mock_fetcher.get_stock_name.return_value = "999999"
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
    # 섹터별 종목에 대해 모킹
    mock_data = {
        "per": 15.0,
        "pbr": 1.5,
    }
    with patch.object(agent, '_fetch_financial_data', return_value=mock_data):
        await agent._calculate_sector_averages()

    # 섹터 평균이 계산됨
    assert "반도체" in agent._sector_averages_cache
    semi_avg = agent._sector_averages_cache["반도체"]
    assert semi_avg["per"] is not None
    assert semi_avg["pbr"] is not None


@pytest.mark.asyncio
async def test_get_sector_average(agent, mock_fetcher):
    """섹터 평균 조회 테스트"""
    mock_data = {"per": 15.0, "pbr": 1.5}
    with patch.object(agent, '_fetch_financial_data', return_value=mock_data):
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


@pytest.mark.asyncio
async def test_cache_set_on_miss(mock_cache, mock_fetcher):
    """캐시 미스 시 저장 테스트"""
    agent = FundamentalAgent(cache=mock_cache, fetcher=mock_fetcher)

    with patch.object(agent, '_fetch_from_naver', return_value=MOCK_NAVER_DATA["005930"]):
        await agent._collect_single("005930")

    # 캐시 저장 호출됨
    mock_cache.set.assert_called()


# =============================================================================
# 재무 데이터 가져오기 테스트
# =============================================================================


def test_fetch_financial_data(agent, mock_fetcher):
    """재무 데이터 가져오기 테스트 (네이버 금융 크롤링)"""
    with patch.object(agent, '_fetch_from_naver', return_value=MOCK_NAVER_DATA["005930"]):
        data = agent._fetch_financial_data("005930")

    # 네이버 금융에서 PER, PBR 가져옴
    assert data.get("per") == 15.0
    assert data.get("pbr") == 1.5
    assert data.get("roe") == 10.0
    assert data.get("debt_ratio") == 30.0


def test_fetch_financial_data_empty_response(agent, mock_fetcher):
    """네이버 금융 응답 없음 테스트"""
    with patch.object(agent, '_fetch_from_naver', return_value={}):
        data = agent._fetch_financial_data("123456")

    # 빈 딕셔너리 반환
    assert data == {}


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
