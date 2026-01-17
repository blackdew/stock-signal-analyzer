"""
Market Data Agent

주가, 기술적 지표, 수급 데이터를 수집하는 에이전트.
FinanceDataReader를 활용하여 KOSPI/KOSDAQ 시총 상위 종목 및
외국인/기관 순매수 데이터를 조회합니다.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import pandas_ta as ta

from src.agents.base_agent import BaseAgent
from src.data.cache import CacheManager, CacheTTL
from src.data.fetcher import StockDataFetcher

try:
    import FinanceDataReader as fdr
except ImportError:
    fdr = None


# =============================================================================
# 데이터 구조 정의
# =============================================================================


@dataclass
class MarketData:
    """시장 데이터 구조"""

    symbol: str
    name: str
    market: str  # KOSPI, KOSDAQ

    # 시가총액 정보
    market_cap: Optional[float] = None  # 시가총액 (억원)
    market_cap_rank: Optional[int] = None  # 시총 순위

    # 가격 데이터
    current_price: Optional[float] = None
    price_change_pct: Optional[float] = None  # 전일 대비 등락률 (%)

    # 기술적 지표 (기존)
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    rsi: Optional[float] = None

    # 기술적 지표 (V2 추가)
    macd: Optional[float] = None           # MACD 값
    macd_signal: Optional[float] = None    # MACD 시그널 라인
    adx: Optional[float] = None            # ADX (추세 강도)
    atr: Optional[float] = None            # ATR (변동성)
    atr_pct: Optional[float] = None        # ATR 퍼센트 (현재가 대비)

    # 리스크 지표 (V2 추가)
    beta: Optional[float] = None           # 베타 (시장 대비)
    max_drawdown_pct: Optional[float] = None  # 최대 낙폭 (%)
    return_20d: Optional[float] = None     # 20일 수익률 (%)

    # 수급 데이터 (최근 5일)
    foreign_net_buy: List[float] = field(default_factory=list)  # 외국인 순매수 (억원)
    institution_net_buy: List[float] = field(default_factory=list)  # 기관 순매수 (억원)

    # 거래 데이터
    volume: Optional[int] = None
    avg_volume_20d: Optional[int] = None
    trading_value: Optional[float] = None  # 거래대금 (억원)


@dataclass
class MarketCapRanking:
    """시가총액 순위"""

    kospi_top20: List[str] = field(default_factory=list)  # 종목코드 리스트
    kosdaq_top10: List[str] = field(default_factory=list)


# =============================================================================
# MarketDataAgent
# =============================================================================


@dataclass
class MarketDataAgent(BaseAgent):
    """
    시장 데이터 수집 에이전트

    주요 기능:
    - 시가총액 순위 조회 (KOSPI/KOSDAQ)
    - 주가 및 기술적 지표 수집 (MA20, MA60, RSI)
    - 외국인/기관 수급 데이터 수집

    사용 예시:
        agent = MarketDataAgent()

        # 시총 순위 조회
        ranking = await agent.get_market_cap_ranking()

        # 종목 데이터 수집
        data = await agent.collect(["005930", "000660"])
    """

    fetcher: StockDataFetcher = field(default_factory=StockDataFetcher)
    analysis_days: int = 180  # 분석 기간 (일)

    async def collect(self, symbols: List[str]) -> Dict[str, MarketData]:
        """
        여러 종목의 시장 데이터를 수집합니다.

        Args:
            symbols: 종목 코드 리스트

        Returns:
            종목코드를 키로 하는 MarketData 딕셔너리
        """
        self._log_info(f"Collecting market data for {len(symbols)} symbols")
        result: Dict[str, MarketData] = {}

        # 날짜 범위 계산
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.analysis_days)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        for symbol in symbols:
            try:
                market_data = await self._collect_single(symbol, start_str, end_str)
                if market_data:
                    result[symbol] = market_data
            except Exception as e:
                self._log_error(f"Failed to collect data for {symbol}: {e}")

        self._log_info(f"Collected market data for {len(result)}/{len(symbols)} symbols")
        return result

    async def _collect_single(
        self, symbol: str, start_date: str, end_date: str
    ) -> Optional[MarketData]:
        """
        단일 종목의 시장 데이터를 수집합니다.
        """
        cache_key = f"market_data_{symbol}"

        # 캐시 확인
        cached = self.cache.get(cache_key, max_age_hours=CacheTTL.PRICE)
        if cached:
            self._log_debug(f"Cache hit for {symbol}")
            return MarketData(**cached)

        # 데이터 수집
        self._log_debug(f"Fetching data for {symbol}")

        # 1. 주가 데이터 가져오기
        df = self.fetcher.fetch_stock_data(symbol, start_date, end_date)
        if df is None or df.empty:
            self._log_warning(f"No price data for {symbol}")
            return None

        # 2. 종목 정보
        name = self.fetcher.get_stock_name(symbol)
        market = self._detect_market(symbol)

        # 3. 기술적 지표 계산
        df = self._calculate_indicators(df)

        # 4. 수급 데이터 (최근 5일)
        foreign_net, inst_net = self._get_supply_data(symbol)

        # 5. 최신 데이터 추출
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        # 6. 거래대금 계산 (현재가 * 거래량 / 억원)
        current_price = float(latest["Close"])
        volume = int(latest["Volume"])
        trading_value = (current_price * volume) / 100_000_000

        # 7. 시가총액 조회
        market_cap, market_cap_rank = self._get_market_cap_info(symbol, market)

        # V2 지표 추출
        macd = float(latest["MACD"]) if pd.notna(latest.get("MACD")) else None
        macd_signal = float(latest["MACD_Signal"]) if pd.notna(latest.get("MACD_Signal")) else None
        adx = float(latest["ADX"]) if pd.notna(latest.get("ADX")) else None
        atr = float(latest["ATR"]) if pd.notna(latest.get("ATR")) else None
        atr_pct = (atr / current_price * 100) if atr and current_price else None
        return_20d = float(latest["Return_20d"]) if pd.notna(latest.get("Return_20d")) else None
        max_drawdown = float(latest["Max_Drawdown"]) if pd.notna(latest.get("Max_Drawdown")) else None

        # 8. 베타 계산 (시장 대비)
        beta = self._calculate_beta(df, symbol)

        # MarketData 생성
        market_data = MarketData(
            symbol=symbol,
            name=name,
            market=market,
            market_cap=market_cap,
            market_cap_rank=market_cap_rank,
            current_price=current_price,
            price_change_pct=self._calculate_change_pct(latest["Close"], prev["Close"]),
            ma20=float(latest["MA20"]) if pd.notna(latest.get("MA20")) else None,
            ma60=float(latest["MA60"]) if pd.notna(latest.get("MA60")) else None,
            rsi=float(latest["RSI"]) if pd.notna(latest.get("RSI")) else None,
            # V2 지표
            macd=macd,
            macd_signal=macd_signal,
            adx=adx,
            atr=atr,
            atr_pct=round(atr_pct, 2) if atr_pct else None,
            beta=beta,
            max_drawdown_pct=round(max_drawdown, 2) if max_drawdown else None,
            return_20d=round(return_20d, 2) if return_20d else None,
            # 수급 데이터
            foreign_net_buy=foreign_net,
            institution_net_buy=inst_net,
            volume=volume,
            avg_volume_20d=int(latest["Volume_MA20"]) if pd.notna(latest.get("Volume_MA20")) else None,
            trading_value=round(trading_value, 2),
        )

        # 캐시 저장 (직렬화 가능한 형태로)
        cache_data = {
            "symbol": market_data.symbol,
            "name": market_data.name,
            "market": market_data.market,
            "market_cap": market_data.market_cap,
            "market_cap_rank": market_data.market_cap_rank,
            "current_price": market_data.current_price,
            "price_change_pct": market_data.price_change_pct,
            "ma20": market_data.ma20,
            "ma60": market_data.ma60,
            "rsi": market_data.rsi,
            # V2 지표
            "macd": market_data.macd,
            "macd_signal": market_data.macd_signal,
            "adx": market_data.adx,
            "atr": market_data.atr,
            "atr_pct": market_data.atr_pct,
            "beta": market_data.beta,
            "max_drawdown_pct": market_data.max_drawdown_pct,
            "return_20d": market_data.return_20d,
            # 수급 데이터
            "foreign_net_buy": market_data.foreign_net_buy,
            "institution_net_buy": market_data.institution_net_buy,
            "volume": market_data.volume,
            "avg_volume_20d": market_data.avg_volume_20d,
            "trading_value": market_data.trading_value,
        }
        self.cache.set(cache_key, cache_data, ttl_hours=CacheTTL.PRICE)

        return market_data

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        기술적 지표를 계산합니다.

        기본 지표: MA20, MA60, RSI
        V2 추가 지표: MACD, ADX, ATR
        """
        if df is None or df.empty:
            return df

        df = df.copy()

        # 이동평균선
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["MA60"] = df["Close"].rolling(window=60).mean()

        # 거래량 이동평균
        df["Volume_MA20"] = df["Volume"].rolling(window=20).mean()

        # RSI (14일 기준)
        try:
            df["RSI"] = ta.rsi(df["Close"], length=14)
        except Exception as e:
            self._log_warning(f"RSI calculation failed: {e}")
            df["RSI"] = None

        # MACD (12, 26, 9)
        try:
            macd_result = ta.macd(df["Close"], fast=12, slow=26, signal=9)
            if macd_result is not None:
                df["MACD"] = macd_result.iloc[:, 0]  # MACD line
                df["MACD_Signal"] = macd_result.iloc[:, 2]  # Signal line
        except Exception as e:
            self._log_warning(f"MACD calculation failed: {e}")
            df["MACD"] = None
            df["MACD_Signal"] = None

        # ADX (14일 기준)
        try:
            adx_result = ta.adx(df["High"], df["Low"], df["Close"], length=14)
            if adx_result is not None:
                df["ADX"] = adx_result.iloc[:, 0]  # ADX
        except Exception as e:
            self._log_warning(f"ADX calculation failed: {e}")
            df["ADX"] = None

        # ATR (14일 기준)
        try:
            df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
        except Exception as e:
            self._log_warning(f"ATR calculation failed: {e}")
            df["ATR"] = None

        # 20일 수익률
        try:
            df["Return_20d"] = df["Close"].pct_change(periods=20) * 100
        except Exception as e:
            self._log_warning(f"20d return calculation failed: {e}")
            df["Return_20d"] = None

        # 최대 낙폭 (Maximum Drawdown) 계산
        try:
            rolling_max = df["Close"].rolling(window=60, min_periods=1).max()
            drawdown = (df["Close"] - rolling_max) / rolling_max * 100
            df["Max_Drawdown"] = drawdown.rolling(window=60, min_periods=1).min().abs()
        except Exception as e:
            self._log_warning(f"Max drawdown calculation failed: {e}")
            df["Max_Drawdown"] = None

        return df

    def _detect_market(self, symbol: str) -> str:
        """
        종목 코드로 시장을 추정합니다.
        """
        try:
            krx = self.fetcher._get_krx_listing()
            stock = krx[krx["Code"] == symbol]
            if not stock.empty and "Market" in stock.columns:
                market = stock.iloc[0]["Market"]
                if pd.notna(market):
                    return str(market).upper()
        except Exception:
            pass

        # 코드로 추정 (5자리: KOSPI, 6자리 3으로 시작: KOSDAQ)
        if len(symbol) == 6 and symbol.startswith("3"):
            return "KOSDAQ"
        return "KOSPI"

    def _get_supply_data(self, symbol: str) -> tuple:
        """
        외국인/기관 순매수 데이터를 가져옵니다 (최근 5일).

        Returns:
            (외국인 순매수 리스트, 기관 순매수 리스트) - 각각 억원 단위
        """
        cache_key = f"supply_{symbol}"
        cached = self.cache.get(cache_key, max_age_hours=CacheTTL.SUPPLY)
        if cached:
            return cached.get("foreign", []), cached.get("institution", [])

        foreign_net = []
        inst_net = []

        try:
            if fdr is None:
                return foreign_net, inst_net

            # 최근 30일 데이터 요청 (5 거래일 확보)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            # 외국인 매매 동향
            try:
                foreign_df = fdr.DataReader(
                    symbol,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    data_source="naver-frgn"  # 네이버 외국인 데이터
                )
                if foreign_df is not None and not foreign_df.empty:
                    # 최근 5일 순매수 (억원 단위로 변환)
                    if "NetPurchase" in foreign_df.columns:
                        foreign_net = (foreign_df["NetPurchase"].tail(5) / 100_000_000).tolist()
                    elif "Foreign_Net" in foreign_df.columns:
                        foreign_net = (foreign_df["Foreign_Net"].tail(5) / 100_000_000).tolist()
            except Exception as e:
                self._log_debug(f"Foreign data fetch failed for {symbol}: {e}")

            # 기관 매매 동향
            try:
                inst_df = fdr.DataReader(
                    symbol,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    data_source="naver-inst"  # 네이버 기관 데이터
                )
                if inst_df is not None and not inst_df.empty:
                    if "NetPurchase" in inst_df.columns:
                        inst_net = (inst_df["NetPurchase"].tail(5) / 100_000_000).tolist()
                    elif "Inst_Net" in inst_df.columns:
                        inst_net = (inst_df["Inst_Net"].tail(5) / 100_000_000).tolist()
            except Exception as e:
                self._log_debug(f"Institution data fetch failed for {symbol}: {e}")

            # 캐시 저장
            if foreign_net or inst_net:
                self.cache.set(
                    cache_key,
                    {"foreign": foreign_net, "institution": inst_net},
                    ttl_hours=CacheTTL.SUPPLY
                )

        except Exception as e:
            self._log_warning(f"Supply data fetch failed for {symbol}: {e}")

        return foreign_net, inst_net

    def _get_market_cap_info(self, symbol: str, market: str) -> tuple:
        """
        시가총액 및 순위 정보를 가져옵니다.

        Returns:
            (시가총액 억원, 순위)
        """
        try:
            listing = self.fetcher._get_krx_listing()
            stock = listing[listing["Code"] == symbol]

            if stock.empty:
                return None, None

            row = stock.iloc[0]

            # 시가총액 컬럼 찾기
            market_cap = None
            for col in ["Marcap", "Market", "MarketCap"]:
                if col in row.index and pd.notna(row[col]):
                    market_cap = row[col] / 100_000_000  # 억원
                    break

            # 순위 계산 (해당 시장 내)
            market_cap_rank = None
            if market_cap and market:
                market_stocks = listing[listing["Market"] == market] if "Market" in listing.columns else listing
                for col in ["Marcap", "Market", "MarketCap"]:
                    if col in market_stocks.columns:
                        sorted_df = market_stocks.sort_values(col, ascending=False).reset_index(drop=True)
                        rank_df = sorted_df[sorted_df["Code"] == symbol]
                        if not rank_df.empty:
                            market_cap_rank = rank_df.index[0] + 1
                        break

            return market_cap, market_cap_rank

        except Exception as e:
            self._log_debug(f"Market cap info fetch failed for {symbol}: {e}")
            return None, None

    def _calculate_change_pct(self, current: float, previous: float) -> Optional[float]:
        """전일 대비 등락률 계산"""
        if previous and previous != 0:
            return round(((current - previous) / previous) * 100, 2)
        return None

    async def get_market_cap_ranking(self) -> MarketCapRanking:
        """
        KOSPI 상위 20개, KOSDAQ 상위 10개 종목을 조회합니다.

        Returns:
            MarketCapRanking 객체
        """
        cache_key = "market_cap_ranking"
        cached = self.cache.get(cache_key, max_age_hours=CacheTTL.MARKET_CAP)
        if cached:
            return MarketCapRanking(**cached)

        self._log_info("Fetching market cap ranking...")

        kospi_top20 = []
        kosdaq_top10 = []

        try:
            # KOSPI 상위 20개
            kospi_stocks = self.fetcher.get_market_cap_rank(market="KOSPI", top_n=20)
            kospi_top20 = [s.symbol for s in kospi_stocks]

            # KOSDAQ 상위 10개
            kosdaq_stocks = self.fetcher.get_market_cap_rank(market="KOSDAQ", top_n=10)
            kosdaq_top10 = [s.symbol for s in kosdaq_stocks]

        except Exception as e:
            self._log_error(f"Failed to fetch market cap ranking: {e}")

        ranking = MarketCapRanking(
            kospi_top20=kospi_top20,
            kosdaq_top10=kosdaq_top10
        )

        # 캐시 저장
        self.cache.set(
            cache_key,
            {"kospi_top20": kospi_top20, "kosdaq_top10": kosdaq_top10},
            ttl_hours=CacheTTL.MARKET_CAP
        )

        self._log_info(
            f"Market cap ranking: KOSPI top {len(kospi_top20)}, "
            f"KOSDAQ top {len(kosdaq_top10)}"
        )

        return ranking

    def _calculate_beta(self, stock_df: pd.DataFrame, symbol: str) -> Optional[float]:
        """
        종목의 베타를 계산합니다 (KOSPI 대비).

        베타 = Cov(종목 수익률, 시장 수익률) / Var(시장 수익률)

        Args:
            stock_df: 종목 주가 데이터프레임
            symbol: 종목 코드

        Returns:
            베타 값 (None if 계산 실패)
        """
        try:
            if fdr is None:
                return None

            # 종목 일간 수익률
            stock_returns = stock_df["Close"].pct_change().dropna()
            if len(stock_returns) < 60:
                return None

            # KOSPI 지수 데이터 가져오기
            start_date = stock_df.index[0].strftime("%Y-%m-%d")
            end_date = stock_df.index[-1].strftime("%Y-%m-%d")

            kospi_df = fdr.DataReader("KS11", start_date, end_date)
            if kospi_df is None or kospi_df.empty:
                return None

            # KOSPI 일간 수익률
            kospi_returns = kospi_df["Close"].pct_change().dropna()

            # 날짜 정렬 및 공통 날짜만 선택
            common_dates = stock_returns.index.intersection(kospi_returns.index)
            if len(common_dates) < 60:
                return None

            stock_r = stock_returns.loc[common_dates]
            market_r = kospi_returns.loc[common_dates]

            # 베타 계산
            covariance = stock_r.cov(market_r)
            market_variance = market_r.var()

            if market_variance == 0:
                return None

            beta = covariance / market_variance
            return round(beta, 2)

        except Exception as e:
            self._log_debug(f"Beta calculation failed for {symbol}: {e}")
            return None
