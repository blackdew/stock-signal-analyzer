"""
Sector Fetcher

네이버 금융에서 업종별 종목을 동적으로 가져옵니다.
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# =============================================================================
# 섹터-업종 매핑
# =============================================================================

# 우리 섹터 → 네이버 금융 업종 코드(들) 매핑
# 하나의 섹터가 여러 업종에 걸칠 수 있음
SECTOR_TO_NAVER_CODES: Dict[str, List[str]] = {
    "반도체": ["278"],  # 반도체와반도체장비
    "조선": ["291"],  # 조선
    "방산/우주": ["284"],  # 우주항공과국방
    "전력인프라": ["306", "325"],  # 전기장비, 전기유틸리티
    "바이오": ["286", "261"],  # 생물공학, 제약
    "로봇": ["282", "299"],  # 전자장비와기기, 기계
    "자동차": ["273", "270"],  # 자동차, 자동차부품
    "신재생에너지": ["295", "306"],  # 에너지장비및서비스, 전기장비
    "지주": ["276"],  # 복합기업
    "뷰티": ["274"],  # 섬유,의류,신발,호화품 (화장품 포함)
    "금융": ["301", "321", "315", "330"],  # 은행, 증권, 손해보험, 생명보험
    "푸드": ["268", "309"],  # 식품, 음료
    "엔터": ["285", "263"],  # 방송과엔터테인먼트, 게임엔터테인먼트
}


@dataclass
class SectorStock:
    """섹터 종목 정보"""
    symbol: str
    name: str
    market_cap: float = 0.0  # 억원 (별도 조회 필요)
    current_price: int = 0
    change_pct: float = 0.0


class SectorFetcher:
    """
    네이버 금융에서 업종별 종목을 가져옵니다.
    """

    BASE_URL = "https://finance.naver.com/sise/sise_group_detail.naver"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    def __init__(self, request_delay: float = 0.3):
        self.request_delay = request_delay
        self._cache: Dict[str, List[SectorStock]] = {}
        self._fetcher = None  # StockDataFetcher (lazy init)

    def _get_fetcher(self):
        """StockDataFetcher 지연 초기화"""
        if self._fetcher is None:
            from src.data.fetcher import StockDataFetcher
            self._fetcher = StockDataFetcher()
        return self._fetcher

    def get_sector_stocks(
        self,
        sector_name: str,
        top_n: int = 10,
        use_cache: bool = True,
        fetch_market_cap: bool = True,
    ) -> List[SectorStock]:
        """
        섹터의 시총 상위 종목을 가져옵니다.

        Args:
            sector_name: 섹터명 (반도체, 조선, 바이오 등)
            top_n: 가져올 종목 수
            use_cache: 캐시 사용 여부
            fetch_market_cap: 시총 조회 여부 (True면 시총 순 정렬)

        Returns:
            SectorStock 리스트 (시총 순)
        """
        cache_key = f"{sector_name}_{top_n}_{fetch_market_cap}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        naver_codes = SECTOR_TO_NAVER_CODES.get(sector_name, [])
        if not naver_codes:
            logger.warning(f"Unknown sector: {sector_name}")
            return []

        all_stocks: List[SectorStock] = []

        for code in naver_codes:
            stocks = self._fetch_sector_stocks(code)
            all_stocks.extend(stocks)
            if len(naver_codes) > 1:
                time.sleep(self.request_delay)

        # 중복 제거 (symbol 기준)
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
            if stock.symbol not in seen:
                seen.add(stock.symbol)
                unique_stocks.append(stock)

        # 시총 조회 및 정렬
        if fetch_market_cap and unique_stocks:
            logger.info(f"Fetching market cap for {len(unique_stocks)} stocks in {sector_name}")
            fetcher = self._get_fetcher()
            for stock in unique_stocks:
                try:
                    market_cap = fetcher.get_market_cap(stock.symbol)
                    stock.market_cap = market_cap if market_cap else 0.0
                except Exception as e:
                    logger.debug(f"Failed to get market cap for {stock.symbol}: {e}")
                    stock.market_cap = 0.0
                time.sleep(0.1)  # 속도 제한

            # 시총 순 정렬
            unique_stocks.sort(key=lambda x: x.market_cap, reverse=True)

        # 상위 N개
        result = unique_stocks[:top_n]

        self._cache[cache_key] = result
        return result

    def get_sector_symbols(
        self,
        sector_name: str,
        top_n: int = 10,
    ) -> List[str]:
        """
        섹터의 시총 상위 종목 코드만 가져옵니다.

        Args:
            sector_name: 섹터명
            top_n: 가져올 종목 수

        Returns:
            종목 코드 리스트
        """
        stocks = self.get_sector_stocks(sector_name, top_n=top_n)
        return [s.symbol for s in stocks]

    def _fetch_sector_stocks(self, naver_code: str) -> List[SectorStock]:
        """네이버 금융에서 업종별 종목을 크롤링합니다."""
        stocks: List[SectorStock] = []

        try:
            url = f"{self.BASE_URL}?type=upjong&no={naver_code}"
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.select_one("table.type_5")

            if not table:
                logger.warning(f"No table found for sector code {naver_code}")
                return stocks

            rows = table.select("tr")
            for row in rows:
                # 종목 링크 찾기
                name_elem = row.select_one('a[href*="main.naver?code="]')
                if not name_elem:
                    continue

                href = name_elem.get("href", "")
                symbol = href.split("code=")[1] if "code=" in href else ""
                name = name_elem.get_text(strip=True).replace("*", "")

                if not symbol or len(symbol) != 6:
                    continue

                # 테이블 컬럼: 종목명, 현재가, 전일비, 등락률, ...
                tds = row.select("td")
                if len(tds) < 4:
                    continue

                try:
                    # 현재가
                    current_price = int(tds[1].get_text(strip=True).replace(",", "") or "0")

                    # 등락률
                    change_text = tds[3].get_text(strip=True).replace("%", "").replace("+", "")
                    change_pct = float(change_text) if change_text else 0.0

                    stocks.append(SectorStock(
                        symbol=symbol,
                        name=name,
                        current_price=current_price,
                        change_pct=change_pct,
                    ))
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse row for {symbol}: {e}")
                    continue

        except requests.RequestException as e:
            logger.error(f"Failed to fetch sector {naver_code}: {e}")
        except Exception as e:
            logger.error(f"Error parsing sector {naver_code}: {e}")

        return stocks

    def get_all_sectors_symbols(
        self,
        top_n_per_sector: int = 10,
    ) -> Dict[str, List[str]]:
        """
        모든 섹터의 종목 코드를 가져옵니다.

        Args:
            top_n_per_sector: 섹터당 가져올 종목 수

        Returns:
            섹터명 → 종목코드 리스트 딕셔너리
        """
        result: Dict[str, List[str]] = {}

        for sector_name in SECTOR_TO_NAVER_CODES.keys():
            logger.info(f"Fetching stocks for sector: {sector_name}")
            symbols = self.get_sector_symbols(sector_name, top_n=top_n_per_sector)
            result[sector_name] = symbols

            # 요청 간격
            time.sleep(self.request_delay)

        return result

    def clear_cache(self):
        """캐시를 비웁니다."""
        self._cache.clear()

    def get_sector_summary(self, sector_name: str, top_n: int = 5) -> str:
        """
        섹터 종목 요약 문자열을 반환합니다.

        Args:
            sector_name: 섹터명
            top_n: 표시할 종목 수

        Returns:
            "삼성전자, SK하이닉스, 한미반도체, ..." 형태의 문자열
        """
        stocks = self.get_sector_stocks(sector_name, top_n=top_n)
        if not stocks:
            return "(종목 없음)"

        names = [s.name for s in stocks[:top_n]]
        return ", ".join(names)
