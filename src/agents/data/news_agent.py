"""
News Agent

뉴스 크롤링 및 센티먼트 분석을 담당하는 에이전트.
네이버 금융 뉴스를 크롤링하고 키워드 기반 센티먼트 분석을 수행합니다.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from src.agents.base_agent import BaseAgent
from src.data.cache import CacheManager
from src.data.fetcher import StockDataFetcher


# =============================================================================
# 캐시 TTL 상수
# =============================================================================

NEWS_CACHE_TTL = 6  # 뉴스 데이터: 6시간


# =============================================================================
# 센티먼트 분석 키워드
# =============================================================================

POSITIVE_KEYWORDS = [
    "급등", "상승", "호재", "수주", "흑자", "성장", "신고가",
    "목표가 상향", "매수 추천", "실적 개선", "계약 체결",
    "호실적", "최대", "사상최대", "돌파", "회복", "상향",
    "기대", "긍정", "수혜", "특수", "대박", "강세",
]

NEGATIVE_KEYWORDS = [
    "급락", "하락", "악재", "적자", "손실", "감소", "신저가",
    "목표가 하향", "매도 추천", "실적 부진", "소송", "리콜",
    "부진", "최저", "사상최저", "이탈", "악화", "하향",
    "우려", "부정", "피해", "위기", "폭락", "약세",
]


# =============================================================================
# 데이터 구조 정의
# =============================================================================


@dataclass
class NewsItem:
    """뉴스 항목"""

    title: str
    url: str
    source: str  # 언론사
    published_at: Optional[datetime] = None
    sentiment: str = "neutral"  # positive, negative, neutral
    sentiment_score: float = 0.0  # -1.0 ~ 1.0


@dataclass
class NewsData:
    """종목별 뉴스 데이터"""

    symbol: str
    name: str
    news_items: List[NewsItem] = field(default_factory=list)

    # 집계 데이터
    total_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    avg_sentiment_score: float = 0.0  # -1.0 ~ 1.0


# =============================================================================
# 센티먼트 분석 함수
# =============================================================================


def classify_sentiment(title: str) -> tuple:
    """
    뉴스 제목 기반 센티먼트 분류

    Args:
        title: 뉴스 제목

    Returns:
        (sentiment: str, score: float)
        - sentiment: "positive", "negative", "neutral"
        - score: -1.0 ~ 1.0
    """
    pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in title)
    neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in title)

    if pos_count > neg_count:
        score = min(1.0, pos_count * 0.3)
        return "positive", score
    elif neg_count > pos_count:
        score = max(-1.0, -neg_count * 0.3)
        return "negative", score
    else:
        return "neutral", 0.0


# =============================================================================
# NewsAgent
# =============================================================================


@dataclass
class NewsAgent(BaseAgent):
    """
    뉴스 수집 및 센티먼트 분석 에이전트

    주요 기능:
    - 네이버 금융 뉴스 크롤링
    - 키워드 기반 센티먼트 분석
    - 크롤링 실패 시 graceful degradation

    사용 예시:
        agent = NewsAgent()
        data = await agent.collect(["005930", "000660"])
    """

    fetcher: StockDataFetcher = field(default_factory=StockDataFetcher)
    request_delay: float = 1.0  # 요청 간격 (초)
    max_news_count: int = 10  # 최대 뉴스 수집 개수

    # 네이버 금융 뉴스 URL 템플릿
    NEWS_URL_TEMPLATE = "https://finance.naver.com/item/news_news.nhn?code={symbol}&page=1"

    # HTTP 헤더
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    async def collect(self, symbols: List[str]) -> Dict[str, NewsData]:
        """
        여러 종목의 뉴스 데이터를 수집합니다.

        Args:
            symbols: 종목 코드 리스트

        Returns:
            종목코드를 키로 하는 NewsData 딕셔너리
        """
        self._log_info(f"Collecting news data for {len(symbols)} symbols")
        result: Dict[str, NewsData] = {}

        for i, symbol in enumerate(symbols):
            try:
                news_data = await self._collect_single(symbol)
                result[symbol] = news_data

                # 요청 간격 딜레이 (마지막 종목 제외)
                if i < len(symbols) - 1:
                    time.sleep(self.request_delay)

            except Exception as e:
                self._log_error(f"Failed to collect news for {symbol}: {e}")
                # 실패 시 중립 데이터 반환
                result[symbol] = self._create_neutral_data(symbol)

        self._log_info(f"Collected news data for {len(result)}/{len(symbols)} symbols")
        return result

    async def _collect_single(self, symbol: str) -> NewsData:
        """
        단일 종목의 뉴스 데이터를 수집합니다.
        """
        cache_key = f"news_{symbol}"

        # 캐시 확인
        cached = self.cache.get(cache_key, max_age_hours=NEWS_CACHE_TTL)
        if cached:
            self._log_debug(f"Cache hit for news_{symbol}")
            return self._dict_to_news_data(cached)

        # 종목명 조회
        name = self.fetcher.get_stock_name(symbol)

        # 뉴스 크롤링
        self._log_debug(f"Fetching news for {symbol} ({name})")
        news_items = self._fetch_news(symbol)

        # NewsData 생성
        news_data = self._create_news_data(symbol, name, news_items)

        # 캐시 저장
        self.cache.set(cache_key, self._news_data_to_dict(news_data), ttl_hours=NEWS_CACHE_TTL)

        return news_data

    def _fetch_news(self, symbol: str) -> List[NewsItem]:
        """
        네이버 금융에서 뉴스를 크롤링합니다.

        Returns:
            NewsItem 리스트 (실패 시 빈 리스트)
        """
        news_items = []

        try:
            url = self.NEWS_URL_TEMPLATE.format(symbol=symbol)
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 뉴스 테이블 찾기
            news_table = soup.select_one("table.type5")
            if not news_table:
                self._log_debug(f"No news table found for {symbol}")
                return news_items

            # 뉴스 행 파싱
            rows = news_table.select("tr")
            for row in rows[:self.max_news_count * 2]:  # 여유있게 가져옴
                if len(news_items) >= self.max_news_count:
                    break

                # 제목 링크 찾기
                title_elem = row.select_one("td.title a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                href = title_elem.get("href", "")

                # URL 정규화
                if href and not href.startswith("http"):
                    href = f"https://finance.naver.com{href}"

                # 언론사
                source_elem = row.select_one("td.info")
                source = source_elem.get_text(strip=True) if source_elem else "Unknown"

                # 날짜
                date_elem = row.select_one("td.date")
                published_at = None
                if date_elem:
                    date_str = date_elem.get_text(strip=True)
                    try:
                        published_at = datetime.strptime(date_str, "%Y.%m.%d %H:%M")
                    except ValueError:
                        pass

                # 센티먼트 분석
                sentiment, score = classify_sentiment(title)

                news_item = NewsItem(
                    title=title,
                    url=href,
                    source=source,
                    published_at=published_at,
                    sentiment=sentiment,
                    sentiment_score=score,
                )
                news_items.append(news_item)

        except requests.RequestException as e:
            self._log_warning(f"News fetch failed for {symbol}: {e}")
        except Exception as e:
            self._log_error(f"News parsing error for {symbol}: {e}")

        return news_items

    def _create_news_data(self, symbol: str, name: str, news_items: List[NewsItem]) -> NewsData:
        """
        NewsData 객체를 생성합니다.
        """
        total_count = len(news_items)
        positive_count = sum(1 for item in news_items if item.sentiment == "positive")
        negative_count = sum(1 for item in news_items if item.sentiment == "negative")
        neutral_count = sum(1 for item in news_items if item.sentiment == "neutral")

        # 평균 센티먼트 점수
        if total_count > 0:
            avg_sentiment_score = sum(item.sentiment_score for item in news_items) / total_count
        else:
            avg_sentiment_score = 0.0

        return NewsData(
            symbol=symbol,
            name=name,
            news_items=news_items,
            total_count=total_count,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            avg_sentiment_score=round(avg_sentiment_score, 3),
        )

    def _create_neutral_data(self, symbol: str) -> NewsData:
        """
        중립 데이터를 생성합니다 (크롤링 실패 시).
        """
        name = self.fetcher.get_stock_name(symbol)
        return NewsData(
            symbol=symbol,
            name=name,
            news_items=[],
            total_count=0,
            positive_count=0,
            negative_count=0,
            neutral_count=0,
            avg_sentiment_score=0.0,
        )

    def _news_data_to_dict(self, news_data: NewsData) -> dict:
        """
        NewsData를 JSON 직렬화 가능한 딕셔너리로 변환합니다.
        """
        return {
            "symbol": news_data.symbol,
            "name": news_data.name,
            "news_items": [
                {
                    "title": item.title,
                    "url": item.url,
                    "source": item.source,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "sentiment": item.sentiment,
                    "sentiment_score": item.sentiment_score,
                }
                for item in news_data.news_items
            ],
            "total_count": news_data.total_count,
            "positive_count": news_data.positive_count,
            "negative_count": news_data.negative_count,
            "neutral_count": news_data.neutral_count,
            "avg_sentiment_score": news_data.avg_sentiment_score,
        }

    def _dict_to_news_data(self, data: dict) -> NewsData:
        """
        딕셔너리를 NewsData로 변환합니다.
        """
        news_items = [
            NewsItem(
                title=item["title"],
                url=item["url"],
                source=item["source"],
                published_at=datetime.fromisoformat(item["published_at"]) if item["published_at"] else None,
                sentiment=item["sentiment"],
                sentiment_score=item["sentiment_score"],
            )
            for item in data.get("news_items", [])
        ]

        return NewsData(
            symbol=data["symbol"],
            name=data["name"],
            news_items=news_items,
            total_count=data.get("total_count", 0),
            positive_count=data.get("positive_count", 0),
            negative_count=data.get("negative_count", 0),
            neutral_count=data.get("neutral_count", 0),
            avg_sentiment_score=data.get("avg_sentiment_score", 0.0),
        )
