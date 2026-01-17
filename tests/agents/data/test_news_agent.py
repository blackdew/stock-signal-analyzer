"""
NewsAgent 테스트

뉴스 수집, 센티먼트 분석, 캐시 동작을 테스트합니다.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.agents.data.news_agent import (
    NewsAgent,
    NewsData,
    NewsItem,
    classify_sentiment,
    POSITIVE_KEYWORDS,
    NEGATIVE_KEYWORDS,
    NEWS_CACHE_TTL,
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
    """NewsAgent 인스턴스"""
    agent = NewsAgent(cache=mock_cache, fetcher=mock_fetcher)
    return agent


@pytest.fixture
def sample_news_html():
    """샘플 뉴스 HTML"""
    return """
    <table class="type5">
        <tr>
            <td class="title">
                <a href="/news?code=1">삼성전자 실적 급등, 사상최대 분기 영업이익</a>
            </td>
            <td class="info">매일경제</td>
            <td class="date">2025.01.17 09:30</td>
        </tr>
        <tr>
            <td class="title">
                <a href="/news?code=2">반도체 업황 부진으로 주가 하락</a>
            </td>
            <td class="info">한국경제</td>
            <td class="date">2025.01.17 10:15</td>
        </tr>
        <tr>
            <td class="title">
                <a href="/news?code=3">삼성전자 주총 개최 예정</a>
            </td>
            <td class="info">연합뉴스</td>
            <td class="date">2025.01.17 11:00</td>
        </tr>
    </table>
    """


# =============================================================================
# 센티먼트 분류 테스트
# =============================================================================


def test_classify_sentiment_positive():
    """긍정 센티먼트 분류 테스트"""
    sentiment, score = classify_sentiment("삼성전자 급등, 신고가 경신")
    assert sentiment == "positive"
    assert score > 0


def test_classify_sentiment_negative():
    """부정 센티먼트 분류 테스트"""
    sentiment, score = classify_sentiment("실적 부진으로 주가 급락")
    assert sentiment == "negative"
    assert score < 0


def test_classify_sentiment_neutral():
    """중립 센티먼트 분류 테스트"""
    sentiment, score = classify_sentiment("삼성전자 주총 개최")
    assert sentiment == "neutral"
    assert score == 0.0


def test_classify_sentiment_multiple_positive():
    """여러 긍정 키워드 테스트"""
    sentiment, score = classify_sentiment("급등 상승 호재 수주")
    assert sentiment == "positive"
    assert score == 1.0  # 4 * 0.3 = 1.2 -> min(1.0, 1.2) = 1.0


def test_classify_sentiment_multiple_negative():
    """여러 부정 키워드 테스트"""
    sentiment, score = classify_sentiment("급락 하락 악재 적자")
    assert sentiment == "negative"
    assert score == -1.0  # -4 * 0.3 = -1.2 -> max(-1.0, -1.2) = -1.0


def test_classify_sentiment_mixed():
    """혼합 키워드 테스트 (긍정이 더 많음)"""
    sentiment, score = classify_sentiment("급등 상승 하락")  # 긍정 2, 부정 1
    assert sentiment == "positive"


def test_classify_sentiment_mixed_negative_wins():
    """혼합 키워드 테스트 (부정이 더 많음)"""
    sentiment, score = classify_sentiment("상승 급락 하락")  # 긍정 1, 부정 2
    assert sentiment == "negative"


# =============================================================================
# NewsItem 테스트
# =============================================================================


def test_news_item_defaults():
    """NewsItem 기본값 테스트"""
    item = NewsItem(title="테스트", url="http://test.com", source="테스트언론")
    assert item.title == "테스트"
    assert item.sentiment == "neutral"
    assert item.sentiment_score == 0.0
    assert item.published_at is None


def test_news_item_with_values():
    """NewsItem 값 설정 테스트"""
    item = NewsItem(
        title="삼성전자 급등",
        url="http://test.com",
        source="매일경제",
        published_at=datetime(2025, 1, 17, 9, 30),
        sentiment="positive",
        sentiment_score=0.6,
    )
    assert item.sentiment == "positive"
    assert item.sentiment_score == 0.6
    assert item.published_at.year == 2025


# =============================================================================
# NewsData 테스트
# =============================================================================


def test_news_data_defaults():
    """NewsData 기본값 테스트"""
    data = NewsData(symbol="005930", name="삼성전자")
    assert data.symbol == "005930"
    assert data.total_count == 0
    assert data.positive_count == 0
    assert data.negative_count == 0
    assert data.neutral_count == 0
    assert data.avg_sentiment_score == 0.0
    assert data.news_items == []


def test_news_data_with_items():
    """NewsData 뉴스 항목 테스트"""
    items = [
        NewsItem("긍정뉴스", "http://1", "A", sentiment="positive", sentiment_score=0.6),
        NewsItem("부정뉴스", "http://2", "B", sentiment="negative", sentiment_score=-0.3),
        NewsItem("중립뉴스", "http://3", "C", sentiment="neutral", sentiment_score=0.0),
    ]
    data = NewsData(
        symbol="005930",
        name="삼성전자",
        news_items=items,
        total_count=3,
        positive_count=1,
        negative_count=1,
        neutral_count=1,
        avg_sentiment_score=0.1,
    )
    assert data.total_count == 3
    assert data.positive_count == 1
    assert len(data.news_items) == 3


# =============================================================================
# 뉴스 수집 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_collect_single_with_cache(mock_cache, mock_fetcher):
    """캐시 히트 테스트"""
    cached_data = {
        "symbol": "005930",
        "name": "삼성전자",
        "news_items": [
            {
                "title": "테스트 뉴스",
                "url": "http://test.com",
                "source": "테스트",
                "published_at": None,
                "sentiment": "neutral",
                "sentiment_score": 0.0,
            }
        ],
        "total_count": 1,
        "positive_count": 0,
        "negative_count": 0,
        "neutral_count": 1,
        "avg_sentiment_score": 0.0,
    }
    mock_cache.get.return_value = cached_data

    agent = NewsAgent(cache=mock_cache, fetcher=mock_fetcher)
    data = await agent._collect_single("005930")

    assert data.symbol == "005930"
    assert data.total_count == 1
    assert len(data.news_items) == 1


@pytest.mark.asyncio
async def test_collect_multiple(agent, mock_fetcher):
    """여러 종목 수집 테스트"""
    with patch.object(agent, "_fetch_news", return_value=[]):
        data = await agent.collect(["005930", "000660"])

    assert isinstance(data, dict)
    assert "005930" in data
    assert "000660" in data


# =============================================================================
# Graceful Degradation 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_graceful_degradation_on_error(agent):
    """크롤링 실패 시 중립 반환 테스트"""
    # _collect_single에서 예외 발생 시뮬레이션
    with patch.object(agent, "_collect_single", side_effect=Exception("Network error")):
        data = await agent.collect(["999999"])

    # 중립 데이터가 반환되어야 함
    assert "999999" in data
    assert data["999999"].avg_sentiment_score == 0.0
    assert data["999999"].total_count == 0


def test_create_neutral_data(agent):
    """중립 데이터 생성 테스트"""
    neutral = agent._create_neutral_data("005930")

    assert neutral.symbol == "005930"
    assert neutral.avg_sentiment_score == 0.0
    assert neutral.total_count == 0
    assert len(neutral.news_items) == 0


# =============================================================================
# 뉴스 파싱 테스트
# =============================================================================


def test_fetch_news_with_mock_response(agent, sample_news_html):
    """뉴스 파싱 테스트"""
    mock_response = Mock()
    mock_response.text = sample_news_html
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        news_items = agent._fetch_news("005930")

    assert len(news_items) == 3

    # 첫 번째 뉴스 확인 (긍정)
    assert "급등" in news_items[0].title
    assert news_items[0].sentiment == "positive"
    assert news_items[0].source == "매일경제"

    # 두 번째 뉴스 확인 (부정)
    assert "하락" in news_items[1].title
    assert news_items[1].sentiment == "negative"

    # 세 번째 뉴스 확인 (중립)
    assert "주총" in news_items[2].title
    assert news_items[2].sentiment == "neutral"


def test_fetch_news_request_failure(agent):
    """네트워크 오류 테스트"""
    import requests

    with patch("requests.get", side_effect=requests.RequestException("Connection failed")):
        news_items = agent._fetch_news("005930")

    assert news_items == []


def test_fetch_news_no_table(agent):
    """뉴스 테이블 없음 테스트"""
    mock_response = Mock()
    mock_response.text = "<html><body>No news</body></html>"
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        news_items = agent._fetch_news("005930")

    assert news_items == []


# =============================================================================
# 데이터 변환 테스트
# =============================================================================


def test_news_data_to_dict(agent):
    """NewsData -> dict 변환 테스트"""
    news_data = NewsData(
        symbol="005930",
        name="삼성전자",
        news_items=[
            NewsItem(
                title="테스트",
                url="http://test.com",
                source="테스트",
                published_at=datetime(2025, 1, 17),
                sentiment="positive",
                sentiment_score=0.6,
            )
        ],
        total_count=1,
        positive_count=1,
        negative_count=0,
        neutral_count=0,
        avg_sentiment_score=0.6,
    )

    result = agent._news_data_to_dict(news_data)

    assert result["symbol"] == "005930"
    assert result["total_count"] == 1
    assert len(result["news_items"]) == 1
    assert result["news_items"][0]["sentiment"] == "positive"


def test_dict_to_news_data(agent):
    """dict -> NewsData 변환 테스트"""
    data = {
        "symbol": "005930",
        "name": "삼성전자",
        "news_items": [
            {
                "title": "테스트",
                "url": "http://test.com",
                "source": "테스트",
                "published_at": "2025-01-17T00:00:00",
                "sentiment": "positive",
                "sentiment_score": 0.6,
            }
        ],
        "total_count": 1,
        "positive_count": 1,
        "negative_count": 0,
        "neutral_count": 0,
        "avg_sentiment_score": 0.6,
    }

    result = agent._dict_to_news_data(data)

    assert isinstance(result, NewsData)
    assert result.symbol == "005930"
    assert result.total_count == 1
    assert len(result.news_items) == 1
    assert result.news_items[0].sentiment == "positive"


# =============================================================================
# 캐시 테스트
# =============================================================================


@pytest.mark.asyncio
async def test_cache_set_on_miss(mock_cache, mock_fetcher):
    """캐시 미스 시 저장 테스트"""
    agent = NewsAgent(cache=mock_cache, fetcher=mock_fetcher)

    with patch.object(agent, "_fetch_news", return_value=[]):
        await agent._collect_single("005930")

    # 캐시 저장 호출됨
    mock_cache.set.assert_called_once()
    call_args = mock_cache.set.call_args
    assert call_args[0][0] == "news_005930"
    assert call_args[1]["ttl_hours"] == NEWS_CACHE_TTL


# =============================================================================
# 키워드 리스트 테스트
# =============================================================================


def test_positive_keywords_exist():
    """긍정 키워드 리스트 확인"""
    assert len(POSITIVE_KEYWORDS) > 0
    assert "급등" in POSITIVE_KEYWORDS
    assert "호재" in POSITIVE_KEYWORDS


def test_negative_keywords_exist():
    """부정 키워드 리스트 확인"""
    assert len(NEGATIVE_KEYWORDS) > 0
    assert "급락" in NEGATIVE_KEYWORDS
    assert "악재" in NEGATIVE_KEYWORDS
