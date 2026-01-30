"""주식 데이터 가져오기 모듈

네이버 금융을 사용하여 주식 데이터를 수집합니다.
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.core.config import SECTORS

# 로거 설정
logger = logging.getLogger(__name__)


# =============================================================================
# 데이터 클래스 정의
# =============================================================================


@dataclass
class StockInfo:
    """종목 기본 정보"""

    symbol: str
    name: str
    market_cap: Optional[float] = None  # 시가총액 (억원)
    sector: Optional[str] = None


@dataclass
class StockData:
    """종목 데이터 (가격 + 지표)"""

    symbol: str
    name: str
    df: pd.DataFrame
    indicators: Optional[Dict[str, Any]] = field(default_factory=dict)


# =============================================================================
# StockDataFetcher 클래스
# =============================================================================


class StockDataFetcher:
    """네이버 금융을 사용하여 주식 데이터를 가져오는 클래스"""

    def __init__(self):
        self._stock_name_cache: Dict[str, str] = {}
        self._market_cap_cache: Dict[str, float] = {}
        self._sector_cache: Dict[str, str] = {}  # 섹터 캐시 추가
        self._latest_trading_date_cache: Optional[str] = None
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    def _get_latest_trading_date(self) -> str:
        """
        네이버 금융에서 가장 최근 거래일을 조회합니다.

        Returns:
            최근 거래일 (YYYYMMDD 형식)
        """
        if self._latest_trading_date_cache:
            return self._latest_trading_date_cache

        try:
            # 삼성전자 일별 시세에서 최근 거래일 추출
            url = "https://finance.naver.com/item/sise_day.naver?code=005930&page=1"
            response = requests.get(url, headers=self._headers, timeout=10)
            response.encoding = "euc-kr"
            soup = BeautifulSoup(response.text, "html.parser")

            for tr in soup.select("table.type2 tr"):
                tds = tr.select("td")
                if len(tds) >= 7:
                    date_text = tds[0].text.strip()
                    if date_text and "." in date_text:
                        # 2026.01.19 -> 20260119
                        date_str = date_text.replace(".", "")
                        self._latest_trading_date_cache = date_str
                        logger.debug(f"최근 거래일: {date_str}")
                        return date_str

        except Exception as e:
            logger.warning(f"최근 거래일 조회 실패: {e}")

        # 폴백: 고정 날짜
        logger.warning("최근 거래일 조회 실패, 기본값 사용")
        self._latest_trading_date_cache = "20250117"
        return self._latest_trading_date_cache

    def fetch_stock_data(
        self, symbol: str, start_date: str, end_date: str, max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        네이버 금융에서 주식 데이터를 가져옵니다.

        Args:
            symbol: 종목 코드 (예: '005930' for 삼성전자)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            max_retries: 최대 재시도 횟수 (기본 3회)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
            실패시 None 반환
        """
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"종목 {symbol}: 데이터 가져오기 시도 {attempt + 1}/{max_retries}"
                )

                all_rows = []
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")

                # 페이지별로 데이터 수집 (최대 20페이지)
                for page in range(1, 21):
                    url = f"https://finance.naver.com/item/sise_day.naver?code={symbol}&page={page}"
                    response = requests.get(url, headers=self._headers, timeout=10)
                    response.encoding = "euc-kr"
                    soup = BeautifulSoup(response.text, "html.parser")

                    page_rows = []
                    for tr in soup.select("table.type2 tr"):
                        tds = tr.select("td")
                        if len(tds) >= 7:
                            date_text = tds[0].text.strip()
                            if date_text and "." in date_text:
                                try:
                                    # 날짜 파싱
                                    row_date = datetime.strptime(date_text, "%Y.%m.%d")

                                    # 날짜 범위 체크
                                    if row_date < start_dt:
                                        # 시작일보다 이전이면 수집 종료
                                        break
                                    if row_date > end_dt:
                                        # 종료일보다 이후면 스킵
                                        continue

                                    close = int(tds[1].text.strip().replace(",", ""))
                                    open_price = int(tds[3].text.strip().replace(",", ""))
                                    high = int(tds[4].text.strip().replace(",", ""))
                                    low = int(tds[5].text.strip().replace(",", ""))
                                    volume = int(tds[6].text.strip().replace(",", ""))

                                    page_rows.append({
                                        "Date": row_date,
                                        "Open": open_price,
                                        "High": high,
                                        "Low": low,
                                        "Close": close,
                                        "Volume": volume,
                                    })
                                except (ValueError, IndexError):
                                    continue

                    if not page_rows:
                        break

                    all_rows.extend(page_rows)

                    # 시작일에 도달했으면 종료
                    if page_rows and page_rows[-1]["Date"] <= start_dt:
                        break

                    time.sleep(0.1)  # 요청 간격

                if not all_rows:
                    logger.warning(
                        f"종목 {symbol}: 데이터 없음 (시도 {attempt + 1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return None

                # DataFrame 생성
                df = pd.DataFrame(all_rows)
                df.set_index("Date", inplace=True)
                df.sort_index(inplace=True)

                logger.debug(
                    f"종목 {symbol}: 데이터 가져오기 성공 "
                    f"({len(df)} 행, {start_date} ~ {end_date})"
                )
                return df

            except Exception as e:
                logger.error(
                    f"종목 {symbol}: 크롤링 실패 - {str(e)} "
                    f"(시도 {attempt + 1}/{max_retries})"
                )

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.debug(f"종목 {symbol}: {wait_time}초 대기 후 재시도...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"종목 {symbol}: 최대 재시도 횟수 초과"
                    )
                    return None

        return None

    def get_stock_name(self, symbol: str) -> str:
        """
        종목 코드로부터 종목명을 가져옵니다.

        Args:
            symbol: 종목 코드

        Returns:
            종목명 (실패시 종목 코드 반환)
        """
        # 캐시 확인
        if symbol in self._stock_name_cache:
            return self._stock_name_cache[symbol]

        try:
            url = f"https://finance.naver.com/item/main.naver?code={symbol}"
            response = requests.get(url, headers=self._headers, timeout=10)
            response.encoding = response.apparent_encoding or "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            # 종목명 추출
            wrap_company = soup.select_one("div.wrap_company h2 a")
            if wrap_company:
                name = wrap_company.text.strip()
                self._stock_name_cache[symbol] = name
                logger.debug(f"종목 {symbol}: 종목명 조회 성공 - {name}")
                return name

        except Exception as e:
            logger.debug(f"종목 {symbol}: 종목명 조회 실패 - {e}")

        logger.warning(f"종목 {symbol}: 종목명 조회 실패 - 종목 코드 사용")
        return symbol

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        기본적인 기술적 지표를 계산합니다.

        Args:
            df: 주가 데이터 DataFrame

        Returns:
            기술적 지표가 추가된 DataFrame
        """
        if df is None or df.empty:
            return df

        # 데이터 복사
        df = df.copy()

        # 이동평균선 계산
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["MA60"] = df["Close"].rolling(window=60).mean()

        # 거래량 이동평균
        df["Volume_MA20"] = df["Volume"].rolling(window=20).mean()

        return df

    def get_market_cap_rank(
        self, market: str = "KOSPI", top_n: int = 20
    ) -> List[StockInfo]:
        """
        시가총액 상위 종목을 조회합니다 (네이버 금융).

        Args:
            market: 시장 구분 ('KOSPI', 'KOSDAQ', 'KRX')
            top_n: 상위 N개 종목 (기본 20개)

        Returns:
            시가총액 상위 종목 리스트 (StockInfo)

        Raises:
            RuntimeError: 조회 실패 시
        """
        logger.debug(f"{market} 시가총액 상위 {top_n}개 종목 조회 중...")

        result = self._get_market_cap_rank_naver(market, top_n)

        if not result:
            raise RuntimeError(f"{market} 시가총액 순위 조회 실패")

        return result

    def _get_market_cap_rank_naver(
        self, market: str, top_n: int
    ) -> List[StockInfo]:
        """네이버 금융에서 시가총액 순위 크롤링"""
        try:
            # 네이버 금융 시가총액 순위 URL
            if market.upper() == "KOSPI":
                url = "https://finance.naver.com/sise/sise_market_sum.naver?sosok=0"
            elif market.upper() == "KOSDAQ":
                url = "https://finance.naver.com/sise/sise_market_sum.naver?sosok=1"
            else:
                # KRX는 KOSPI + KOSDAQ 합산
                kospi = self._get_market_cap_rank_naver("KOSPI", top_n)
                kosdaq = self._get_market_cap_rank_naver("KOSDAQ", top_n)
                combined = kospi + kosdaq
                combined.sort(key=lambda x: x.market_cap or 0, reverse=True)
                return combined[:top_n]

            result = []
            # 첫 페이지만 조회 (상위 50개)
            response = requests.get(url, headers=self._headers, timeout=10)
            response.encoding = "euc-kr"
            soup = BeautifulSoup(response.text, "html.parser")

            table = soup.find("table", class_="type_2")
            if not table:
                logger.warning("네이버 금융 테이블 파싱 실패")
                return []

            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 7:
                    continue

                # 종목 링크에서 코드 추출
                link = cols[1].find("a")
                if not link:
                    continue

                href = link.get("href", "")
                if "code=" not in href:
                    continue

                symbol = href.split("code=")[-1]
                name = link.text.strip()

                # 시가총액 (억원 단위)
                try:
                    market_cap_text = cols[6].text.strip().replace(",", "")
                    market_cap = float(market_cap_text) if market_cap_text else 0
                except (ValueError, IndexError):
                    market_cap = 0

                stock_info = StockInfo(
                    symbol=symbol,
                    name=name,
                    market_cap=market_cap,
                    sector=self._find_sector_by_symbol(symbol),
                )
                result.append(stock_info)

                if len(result) >= top_n:
                    break

            logger.debug(f"{market} 시가총액 상위 {len(result)}개 종목 조회 완료 (네이버)")
            return result

        except Exception as e:
            logger.error(f"네이버 금융 시가총액 순위 조회 실패: {e}")
            return []

    def get_sector_stocks(self, sector_name: str) -> List[StockInfo]:
        """
        섹터별 종목을 조회합니다.

        Args:
            sector_name: 섹터명 (예: "반도체", "조선")

        Returns:
            해당 섹터의 종목 리스트 (StockInfo)
        """
        try:
            logger.debug(f"섹터 '{sector_name}' 종목 조회 중...")

            # config.py의 SECTORS에서 종목 코드 가져오기
            if sector_name not in SECTORS:
                logger.warning(f"섹터 '{sector_name}'이(가) 정의되지 않았습니다.")
                logger.debug(f"사용 가능한 섹터: {list(SECTORS.keys())}")
                return []

            symbols = SECTORS[sector_name]

            result = []
            for symbol in symbols:
                name = self.get_stock_name(symbol)
                stock_info = StockInfo(
                    symbol=symbol,
                    name=name,
                    market_cap=None,
                    sector=sector_name,
                )
                result.append(stock_info)

            logger.debug(f"섹터 '{sector_name}' 종목 {len(result)}개 조회 완료")
            return result

        except Exception as e:
            logger.error(f"섹터 종목 조회 실패: {str(e)}")
            return []

    def _find_sector_by_symbol(self, symbol: str) -> Optional[str]:
        """
        종목 코드로 섹터를 찾습니다.

        우선순위:
        1. config.py의 SECTORS에서 검색 (수동 매핑된 섹터)
        2. 네이버 금융 WiseReport에서 업종 정보 크롤링

        Args:
            symbol: 종목 코드

        Returns:
            섹터명 (찾지 못하면 None)
        """
        # 1. SECTORS에서 먼저 검색 (수동 매핑 우선)
        for sector_name, symbols in SECTORS.items():
            if symbol in symbols:
                return sector_name

        # 2. 캐시 확인
        if symbol in self._sector_cache:
            return self._sector_cache[symbol]

        # 3. 네이버 금융에서 자동 조회
        sector = self._get_sector_from_naver(symbol)
        if sector:
            self._sector_cache[symbol] = sector
            return sector

        return None

    def _get_sector_from_naver(self, symbol: str) -> Optional[str]:
        """
        네이버 금융 WiseReport에서 종목의 업종 정보를 가져옵니다.

        Args:
            symbol: 종목 코드

        Returns:
            업종명 (예: "코스피 전기·전자", "코스닥 제약")
            실패시 None
        """
        try:
            url = f"https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd={symbol}"
            response = requests.get(url, headers=self._headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            # KOSPI/KOSDAQ 업종 정보 추출
            for elem in soup.select("span, dt, dd"):
                text = elem.text.strip()
                if text.startswith("KOSPI :") or text.startswith("KOSDAQ :"):
                    # "KOSPI : 코스피 전기·전자" -> "코스피 전기·전자"
                    sector = text.split(":")[-1].strip()
                    logger.debug(f"종목 {symbol}: 네이버 업종 조회 성공 - {sector}")
                    return sector

            logger.debug(f"종목 {symbol}: 네이버 업종 정보 없음")
            return None

        except Exception as e:
            logger.warning(f"종목 {symbol}: 네이버 업종 조회 실패 - {e}")
            return None

    def fetch_stock_data_with_info(
        self, symbol: str, start_date: str, end_date: str, max_retries: int = 3
    ) -> Optional[StockData]:
        """
        주식 데이터와 종목 정보를 함께 가져옵니다.

        Args:
            symbol: 종목 코드
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            max_retries: 최대 재시도 횟수

        Returns:
            StockData 객체 (실패시 None)
        """
        df = self.fetch_stock_data(symbol, start_date, end_date, max_retries)

        if df is None:
            return None

        # 기술적 지표 계산
        df_with_indicators = self.calculate_technical_indicators(df)

        # 지표 요약 정보 추출
        indicators = {}
        if not df_with_indicators.empty:
            latest = df_with_indicators.iloc[-1]
            indicators = {
                "ma20": latest.get("MA20"),
                "ma60": latest.get("MA60"),
                "volume_ma20": latest.get("Volume_MA20"),
                "current_price": latest.get("Close"),
                "current_volume": latest.get("Volume"),
            }

        return StockData(
            symbol=symbol,
            name=self.get_stock_name(symbol),
            df=df_with_indicators,
            indicators=indicators,
        )

    def get_all_sectors(self) -> List[str]:
        """
        사용 가능한 모든 섹터명을 반환합니다.

        Returns:
            섹터명 리스트
        """
        return list(SECTORS.keys())

    def get_foreign_institution_trading(
        self, symbol: str, days: int = 5
    ) -> tuple:
        """
        외국인/기관 순매수 데이터를 가져옵니다.

        Args:
            symbol: 종목 코드
            days: 조회할 일수 (기본 5일)

        Returns:
            (외국인 순매수 리스트, 기관 순매수 리스트) - 각각 억원 단위
        """
        foreign_net = []
        inst_net = []

        try:
            url = f"https://finance.naver.com/item/frgn.naver?code={symbol}"
            response = requests.get(url, headers=self._headers, timeout=10)
            response.encoding = "euc-kr"
            soup = BeautifulSoup(response.text, "html.parser")

            # 외국인/기관 매매 테이블 파싱 (두 번째 type2 테이블)
            tables = soup.select("table.type2")
            table = tables[1] if len(tables) > 1 else tables[0] if tables else None
            if table:
                rows = table.select("tr")
                count = 0
                for row in rows:
                    tds = row.select("td")
                    if len(tds) >= 9:
                        # 날짜, 종가, 전일비, 등락률, 거래량, 기관순매매, 외국인순매매, 외국인보유, 외국인보유율
                        try:
                            date_text = tds[0].text.strip()
                            if not date_text or "." not in date_text:
                                continue

                            # 기관 순매매 (6번째 컬럼)
                            inst_text = tds[5].text.strip().replace(",", "").replace("+", "")
                            inst_value = int(inst_text) if inst_text and inst_text != "-" else 0

                            # 외국인 순매매 (7번째 컬럼)
                            foreign_text = tds[6].text.strip().replace(",", "").replace("+", "")
                            foreign_value = int(foreign_text) if foreign_text and foreign_text != "-" else 0

                            # 억원 단위로 변환 (주 단위 -> 억원)
                            # 현재가 * 수량 / 1억
                            close_text = tds[1].text.strip().replace(",", "")
                            close = int(close_text) if close_text else 0

                            foreign_net.append(round(foreign_value * close / 100_000_000, 2))
                            inst_net.append(round(inst_value * close / 100_000_000, 2))

                            count += 1
                            if count >= days:
                                break

                        except (ValueError, IndexError):
                            continue

        except Exception as e:
            logger.warning(f"외국인/기관 매매 데이터 조회 실패 for {symbol}: {e}")

        return foreign_net, inst_net

    def get_market_cap(self, symbol: str) -> Optional[float]:
        """
        개별 종목의 시가총액을 조회합니다.

        Args:
            symbol: 종목 코드 (예: '005930')

        Returns:
            시가총액 (억원), 조회 실패시 None
        """
        import re

        # 캐시 확인
        if symbol in self._market_cap_cache:
            return self._market_cap_cache[symbol]

        try:
            # sise.naver 페이지에서 시가총액 조회 (더 안정적)
            url = f"https://finance.naver.com/item/sise.naver?code={symbol}"
            response = requests.get(url, headers=self._headers, timeout=10)
            response.encoding = "euc-kr"
            soup = BeautifulSoup(response.text, "html.parser")

            # em#_market_sum 태그에서 시가총액 추출
            market_sum_em = soup.select_one("em#_market_sum")
            if market_sum_em:
                text = market_sum_em.text.strip().replace("\n", "").replace("\t", "").replace(" ", "")
                # "4조6,020" 형식 파싱
                jo_match = re.search(r"(\d+)조", text)
                jo = int(jo_match.group(1)) if jo_match else 0

                # 조 뒤의 억 단위 추출
                after_jo = text.split("조")[-1] if "조" in text else text
                eok_match = re.search(r"([0-9,]+)", after_jo)
                eok = int(eok_match.group(1).replace(",", "")) if eok_match else 0

                market_cap = float(jo * 10000 + eok)
                self._market_cap_cache[symbol] = market_cap
                logger.debug(f"종목 {symbol}: 시가총액 조회 성공 - {market_cap}억원")
                return market_cap

            logger.debug(f"종목 {symbol}: 시가총액 정보 없음")
            return None

        except Exception as e:
            logger.warning(f"종목 {symbol}: 시가총액 조회 실패 - {e}")
            return None

    def get_dividend_yield(self, symbol: str) -> Optional[float]:
        """
        종목의 배당수익률을 조회합니다 (네이버 금융).

        Args:
            symbol: 종목 코드 (예: '005930')

        Returns:
            배당수익률 (%), 조회 실패시 None
        """
        try:
            url = f"https://finance.naver.com/item/main.naver?code={symbol}"
            response = requests.get(url, headers=self._headers, timeout=10)
            response.encoding = response.apparent_encoding or "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            # 배당수익률 추출 (per_table에서 조회)
            # "배당수익률" 텍스트를 포함하는 th 태그를 찾고 인접 td에서 값 추출
            tables = soup.select("table.per_table")
            for table in tables:
                for tr in table.select("tr"):
                    th = tr.select_one("th")
                    td = tr.select_one("td")
                    if th and td and "배당수익률" in th.text:
                        # "2.15%" -> 2.15
                        yield_text = td.text.strip().replace("%", "").replace(",", "")
                        if yield_text and yield_text not in ("-", "N/A", "n/a", ""):
                            dividend_yield = float(yield_text)
                            logger.debug(f"종목 {symbol}: 배당수익률 조회 성공 - {dividend_yield}%")
                            return dividend_yield

            # 대체 위치: em 태그에서 직접 검색
            for em in soup.select("em"):
                parent_text = em.parent.text if em.parent else ""
                if "배당수익률" in parent_text:
                    yield_text = em.text.strip().replace("%", "").replace(",", "")
                    if yield_text and yield_text not in ("-", "N/A", "n/a", ""):
                        dividend_yield = float(yield_text)
                        logger.debug(f"종목 {symbol}: 배당수익률 조회 성공 - {dividend_yield}%")
                        return dividend_yield

            logger.debug(f"종목 {symbol}: 배당수익률 정보 없음")
            return None

        except Exception as e:
            logger.warning(f"종목 {symbol}: 배당수익률 조회 실패 - {e}")
            return None

    def get_kospi_index(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        KOSPI 지수 데이터를 가져옵니다.

        Args:
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            DataFrame with columns: Close (종가)
        """
        try:
            all_rows = []
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # KOSPI 지수 일별 시세
            for page in range(1, 21):
                url = f"https://finance.naver.com/sise/sise_index_day.naver?code=KOSPI&page={page}"
                response = requests.get(url, headers=self._headers, timeout=10)
                response.encoding = "euc-kr"
                soup = BeautifulSoup(response.text, "html.parser")

                page_rows = []
                for tr in soup.select("table.type_1 tr"):
                    tds = tr.select("td")
                    if len(tds) >= 4:
                        date_text = tds[0].text.strip()
                        if date_text and "." in date_text:
                            try:
                                row_date = datetime.strptime(date_text, "%Y.%m.%d")

                                if row_date < start_dt:
                                    break
                                if row_date > end_dt:
                                    continue

                                close_text = tds[1].text.strip().replace(",", "")
                                close = float(close_text) if close_text else 0

                                page_rows.append({
                                    "Date": row_date,
                                    "Close": close,
                                })
                            except (ValueError, IndexError):
                                continue

                if not page_rows:
                    break

                all_rows.extend(page_rows)

                if page_rows and page_rows[-1]["Date"] <= start_dt:
                    break

                time.sleep(0.1)

            if not all_rows:
                return None

            df = pd.DataFrame(all_rows)
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)

            logger.debug(f"KOSPI 지수 데이터 조회 완료 ({len(df)} 행)")
            return df

        except Exception as e:
            logger.error(f"KOSPI 지수 조회 실패: {e}")
            return None
