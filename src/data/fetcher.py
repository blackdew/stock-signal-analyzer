"""주식 데이터 가져오기 모듈"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import FinanceDataReader as fdr
import pandas as pd

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
    """FinanceDataReader를 사용하여 주식 데이터를 가져오는 클래스"""

    def __init__(self):
        self._krx_listing_cache: Optional[pd.DataFrame] = None

    def _get_krx_listing(self) -> pd.DataFrame:
        """
        KRX 상장 종목 리스트를 가져옵니다 (캐싱 적용).

        Returns:
            KRX 상장 종목 DataFrame
        """
        if self._krx_listing_cache is None:
            logger.debug("KRX 상장 종목 리스트 로딩 중...")
            self._krx_listing_cache = fdr.StockListing("KRX")
            logger.debug(f"KRX 상장 종목 {len(self._krx_listing_cache)}개 로드 완료")
        return self._krx_listing_cache

    def fetch_stock_data(
        self, symbol: str, start_date: str, end_date: str, max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        주식 데이터를 가져옵니다. (재시도 로직 포함)

        Args:
            symbol: 종목 코드 (예: '005930' for 삼성전자)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            max_retries: 최대 재시도 횟수 (기본 3회)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Change
            실패시 None 반환
        """
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"종목 {symbol}: 데이터 가져오기 시도 {attempt + 1}/{max_retries}"
                )
                df = fdr.DataReader(symbol, start_date, end_date)

                # 데이터 검증
                if df is None or df.empty:
                    logger.warning(
                        f"종목 {symbol}: 데이터 없음 (시도 {attempt + 1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(1)  # 1초 대기 후 재시도
                        continue
                    else:
                        logger.error(
                            f"종목 {symbol}: 최대 재시도 횟수 초과 - 데이터 없음"
                        )
                        return None

                # 데이터 정리
                df = df.sort_index()
                logger.info(
                    f"종목 {symbol}: 데이터 가져오기 성공 "
                    f"({len(df)} 행, {start_date} ~ {end_date})"
                )
                return df

            except Exception as e:
                logger.error(
                    f"종목 {symbol}: API 호출 실패 - {str(e)} "
                    f"(시도 {attempt + 1}/{max_retries})"
                )

                if attempt < max_retries - 1:
                    # 지수 백오프 (1초, 2초, 4초)
                    wait_time = 2**attempt
                    logger.info(f"종목 {symbol}: {wait_time}초 대기 후 재시도...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"종목 {symbol}: 최대 재시도 횟수 초과 - API 호출 실패"
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
        try:
            logger.debug(f"종목 {symbol}: 종목명 조회 중...")
            krx = self._get_krx_listing()
            stock_info = krx[krx["Code"] == symbol]

            if not stock_info.empty:
                name = stock_info.iloc[0]["Name"]
                logger.debug(f"종목 {symbol}: 종목명 조회 성공 - {name}")
                return name
            else:
                logger.warning(f"종목 {symbol}: 종목명 조회 실패 - 종목 코드 사용")
                return symbol

        except Exception as e:
            logger.warning(f"종목 {symbol}: 종목명 조회 오류 - {str(e)}")
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
        시가총액 상위 종목을 조회합니다.

        Args:
            market: 시장 구분 ('KOSPI', 'KOSDAQ', 'KRX')
            top_n: 상위 N개 종목 (기본 20개)

        Returns:
            시가총액 상위 종목 리스트 (StockInfo)
        """
        try:
            logger.info(f"{market} 시가총액 상위 {top_n}개 종목 조회 중...")

            # 시장별 데이터 가져오기
            if market.upper() == "KRX":
                listing = self._get_krx_listing()
            else:
                listing = fdr.StockListing(market.upper())

            if listing is None or listing.empty:
                logger.warning(f"{market} 상장 종목 데이터를 가져올 수 없습니다.")
                return []

            # 시가총액 컬럼 확인 및 정렬
            # FinanceDataReader의 컬럼명은 'Marcap' 또는 'Market'
            market_cap_col = None
            for col in ["Marcap", "Market", "MarketCap"]:
                if col in listing.columns:
                    market_cap_col = col
                    break

            if market_cap_col is None:
                logger.warning(
                    f"{market} 데이터에 시가총액 컬럼이 없습니다. "
                    f"컬럼: {listing.columns.tolist()}"
                )
                return []

            # 시가총액 기준 정렬 및 상위 N개 추출
            sorted_listing = listing.nlargest(top_n, market_cap_col)

            result = []
            for _, row in sorted_listing.iterrows():
                # 시가총액을 억원 단위로 변환 (원 단위 -> 억원)
                market_cap_value = row.get(market_cap_col, 0)
                market_cap_billion = (
                    market_cap_value / 100_000_000 if market_cap_value else None
                )

                stock_info = StockInfo(
                    symbol=row.get("Code", row.get("Symbol", "")),
                    name=row.get("Name", ""),
                    market_cap=market_cap_billion,
                    sector=self._find_sector_by_symbol(
                        row.get("Code", row.get("Symbol", ""))
                    ),
                )
                result.append(stock_info)

            logger.info(f"{market} 시가총액 상위 {len(result)}개 종목 조회 완료")
            return result

        except Exception as e:
            logger.error(f"시가총액 순위 조회 실패: {str(e)}")
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
            logger.info(f"섹터 '{sector_name}' 종목 조회 중...")

            # config.py의 SECTORS에서 종목 코드 가져오기
            if sector_name not in SECTORS:
                logger.warning(f"섹터 '{sector_name}'이(가) 정의되지 않았습니다.")
                logger.info(f"사용 가능한 섹터: {list(SECTORS.keys())}")
                return []

            symbols = SECTORS[sector_name]
            krx = self._get_krx_listing()

            result = []
            for symbol in symbols:
                stock_row = krx[krx["Code"] == symbol]

                if not stock_row.empty:
                    row = stock_row.iloc[0]

                    # 시가총액 컬럼 확인
                    market_cap_value = None
                    for col in ["Marcap", "Market", "MarketCap"]:
                        if col in row.index and pd.notna(row[col]):
                            market_cap_value = row[col] / 100_000_000  # 억원 단위
                            break

                    stock_info = StockInfo(
                        symbol=symbol,
                        name=row.get("Name", symbol),
                        market_cap=market_cap_value,
                        sector=sector_name,
                    )
                else:
                    # KRX 리스트에 없는 경우 기본 정보만 생성
                    stock_info = StockInfo(
                        symbol=symbol,
                        name=self.get_stock_name(symbol),
                        market_cap=None,
                        sector=sector_name,
                    )

                result.append(stock_info)

            logger.info(f"섹터 '{sector_name}' 종목 {len(result)}개 조회 완료")
            return result

        except Exception as e:
            logger.error(f"섹터 종목 조회 실패: {str(e)}")
            return []

    def _find_sector_by_symbol(self, symbol: str) -> Optional[str]:
        """
        종목 코드로 섹터를 찾습니다.

        Args:
            symbol: 종목 코드

        Returns:
            섹터명 (찾지 못하면 None)
        """
        for sector_name, symbols in SECTORS.items():
            if symbol in symbols:
                return sector_name
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
