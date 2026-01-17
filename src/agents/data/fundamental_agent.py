"""
Fundamental Agent

재무제표 데이터를 수집하는 에이전트.
FinanceDataReader를 활용하여 PER, PBR, ROE, 부채비율 등을 조회합니다.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from src.agents.base_agent import BaseAgent
from src.data.cache import CacheManager, CacheTTL
from src.data.fetcher import StockDataFetcher
from src.core.config import SECTORS, get_sector_by_symbol

try:
    import FinanceDataReader as fdr
except ImportError:
    fdr = None


# =============================================================================
# 데이터 구조 정의
# =============================================================================


@dataclass
class FundamentalData:
    """재무제표 데이터 구조"""

    symbol: str
    name: str
    sector: Optional[str] = None

    # 밸류에이션
    per: Optional[float] = None  # PER (주가수익비율)
    pbr: Optional[float] = None  # PBR (주가순자산비율)

    # 수익성
    roe: Optional[float] = None  # ROE (자기자본이익률, %)
    operating_margin: Optional[float] = None  # 영업이익률 (%)

    # 성장성
    revenue_growth: Optional[float] = None  # 매출 성장률 (YoY, %)
    operating_profit_growth: Optional[float] = None  # 영업이익 성장률 (YoY, %)

    # 재무건전성
    debt_ratio: Optional[float] = None  # 부채비율 (%)

    # 업종 평균 (비교용)
    sector_avg_per: Optional[float] = None
    sector_avg_pbr: Optional[float] = None


# =============================================================================
# FundamentalAgent
# =============================================================================


@dataclass
class FundamentalAgent(BaseAgent):
    """
    재무제표 데이터 수집 에이전트

    주요 기능:
    - PER, PBR 조회
    - ROE, 영업이익률 조회
    - 매출/영업이익 성장률 계산
    - 부채비율 조회
    - 섹터 평균 계산

    사용 예시:
        agent = FundamentalAgent()
        data = await agent.collect(["005930", "000660"])
    """

    fetcher: StockDataFetcher = field(default_factory=StockDataFetcher)
    _sector_averages_cache: Dict[str, Dict] = field(default_factory=dict)

    async def collect(self, symbols: List[str]) -> Dict[str, FundamentalData]:
        """
        여러 종목의 재무제표 데이터를 수집합니다.

        Args:
            symbols: 종목 코드 리스트

        Returns:
            종목코드를 키로 하는 FundamentalData 딕셔너리
        """
        self._log_info(f"Collecting fundamental data for {len(symbols)} symbols")
        result: Dict[str, FundamentalData] = {}

        # 섹터 평균 사전 계산
        await self._calculate_sector_averages()

        for symbol in symbols:
            try:
                fundamental_data = await self._collect_single(symbol)
                if fundamental_data:
                    result[symbol] = fundamental_data
            except Exception as e:
                self._log_error(f"Failed to collect fundamental data for {symbol}: {e}")

        self._log_info(
            f"Collected fundamental data for {len(result)}/{len(symbols)} symbols"
        )
        return result

    async def _collect_single(self, symbol: str) -> Optional[FundamentalData]:
        """
        단일 종목의 재무제표 데이터를 수집합니다.
        """
        cache_key = f"fundamental_{symbol}"

        # 캐시 확인
        cached = self.cache.get(cache_key, max_age_hours=CacheTTL.FUNDAMENTAL)
        if cached:
            self._log_debug(f"Cache hit for {symbol}")
            return FundamentalData(**cached)

        self._log_debug(f"Fetching fundamental data for {symbol}")

        # 종목 정보
        name = self.fetcher.get_stock_name(symbol)
        sector = get_sector_by_symbol(symbol)
        if sector == "Unknown":
            sector = None

        # 재무 데이터 조회
        financial_data = self._fetch_financial_data(symbol)

        if not financial_data:
            # 데이터가 없어도 기본 정보는 반환
            return FundamentalData(
                symbol=symbol,
                name=name,
                sector=sector
            )

        # 섹터 평균 가져오기
        sector_avg_per = None
        sector_avg_pbr = None
        if sector and sector in self._sector_averages_cache:
            sector_avg = self._sector_averages_cache[sector]
            sector_avg_per = sector_avg.get("per")
            sector_avg_pbr = sector_avg.get("pbr")

        # FundamentalData 생성
        fundamental_data = FundamentalData(
            symbol=symbol,
            name=name,
            sector=sector,
            per=financial_data.get("per"),
            pbr=financial_data.get("pbr"),
            roe=financial_data.get("roe"),
            operating_margin=financial_data.get("operating_margin"),
            revenue_growth=financial_data.get("revenue_growth"),
            operating_profit_growth=financial_data.get("operating_profit_growth"),
            debt_ratio=financial_data.get("debt_ratio"),
            sector_avg_per=sector_avg_per,
            sector_avg_pbr=sector_avg_pbr,
        )

        # 캐시 저장
        cache_data = {
            "symbol": fundamental_data.symbol,
            "name": fundamental_data.name,
            "sector": fundamental_data.sector,
            "per": fundamental_data.per,
            "pbr": fundamental_data.pbr,
            "roe": fundamental_data.roe,
            "operating_margin": fundamental_data.operating_margin,
            "revenue_growth": fundamental_data.revenue_growth,
            "operating_profit_growth": fundamental_data.operating_profit_growth,
            "debt_ratio": fundamental_data.debt_ratio,
            "sector_avg_per": fundamental_data.sector_avg_per,
            "sector_avg_pbr": fundamental_data.sector_avg_pbr,
        }
        self.cache.set(cache_key, cache_data, ttl_hours=CacheTTL.FUNDAMENTAL)

        return fundamental_data

    def _fetch_financial_data(self, symbol: str) -> Dict[str, Any]:
        """
        FinanceDataReader를 사용하여 재무 데이터를 가져옵니다.

        Returns:
            재무 데이터 딕셔너리
        """
        result: Dict[str, Any] = {}

        if fdr is None:
            self._log_warning("FinanceDataReader not available")
            return result

        try:
            # KRX 상장 종목 정보에서 기본 밸류에이션 데이터 가져오기
            krx = self.fetcher._get_krx_listing()
            stock = krx[krx["Code"] == symbol]

            if not stock.empty:
                row = stock.iloc[0]

                # PER
                if "PER" in row.index and pd.notna(row["PER"]):
                    per_value = row["PER"]
                    if per_value > 0:  # 음수 PER 제외
                        result["per"] = round(float(per_value), 2)

                # PBR
                if "PBR" in row.index and pd.notna(row["PBR"]):
                    pbr_value = row["PBR"]
                    if pbr_value > 0:
                        result["pbr"] = round(float(pbr_value), 2)

            # SnapDataReader로 추가 재무 데이터 시도
            snap_data = self._fetch_snap_data(symbol)
            if snap_data:
                result.update(snap_data)

        except Exception as e:
            self._log_warning(f"Financial data fetch failed for {symbol}: {e}")

        return result

    def _fetch_snap_data(self, symbol: str) -> Dict[str, Any]:
        """
        SnapDataReader를 사용하여 상세 재무 데이터를 가져옵니다.
        """
        result: Dict[str, Any] = {}

        try:
            # SnapDataReader 시도 (지원되는 경우)
            if not hasattr(fdr, "SnapDataReader"):
                return result

            snap_df = fdr.SnapDataReader(symbol)

            if snap_df is None or snap_df.empty:
                return result

            # ROE 추출
            if "ROE" in snap_df.columns:
                roe_value = snap_df["ROE"].iloc[0]
                if pd.notna(roe_value):
                    result["roe"] = round(float(roe_value), 2)

            # 영업이익률 추출
            for col in ["영업이익률", "OPM", "OperatingMargin"]:
                if col in snap_df.columns:
                    value = snap_df[col].iloc[0]
                    if pd.notna(value):
                        result["operating_margin"] = round(float(value), 2)
                        break

            # 부채비율 추출
            for col in ["부채비율", "DebtRatio", "Debt Ratio"]:
                if col in snap_df.columns:
                    value = snap_df[col].iloc[0]
                    if pd.notna(value):
                        result["debt_ratio"] = round(float(value), 2)
                        break

            # 매출 성장률 추출
            for col in ["매출액증가율", "RevenueGrowth", "Revenue Growth"]:
                if col in snap_df.columns:
                    value = snap_df[col].iloc[0]
                    if pd.notna(value):
                        result["revenue_growth"] = round(float(value), 2)
                        break

            # 영업이익 성장률 추출
            for col in ["영업이익증가율", "OPGrowth", "Operating Profit Growth"]:
                if col in snap_df.columns:
                    value = snap_df[col].iloc[0]
                    if pd.notna(value):
                        result["operating_profit_growth"] = round(float(value), 2)
                        break

        except Exception as e:
            self._log_debug(f"SnapDataReader failed for {symbol}: {e}")

        return result

    async def _calculate_sector_averages(self) -> None:
        """
        섹터별 평균 PER, PBR을 계산합니다.
        """
        if self._sector_averages_cache:
            return  # 이미 계산됨

        self._log_info("Calculating sector averages...")

        for sector_name, symbols in SECTORS.items():
            per_values = []
            pbr_values = []

            for symbol in symbols:
                data = self._fetch_financial_data(symbol)
                if data.get("per"):
                    per_values.append(data["per"])
                if data.get("pbr"):
                    pbr_values.append(data["pbr"])

            self._sector_averages_cache[sector_name] = {
                "per": round(sum(per_values) / len(per_values), 2) if per_values else None,
                "pbr": round(sum(pbr_values) / len(pbr_values), 2) if pbr_values else None,
            }

        self._log_info(f"Calculated averages for {len(self._sector_averages_cache)} sectors")

    def get_sector_average(self, sector: str) -> Dict[str, Optional[float]]:
        """
        특정 섹터의 평균 밸류에이션을 반환합니다.

        Args:
            sector: 섹터명

        Returns:
            {"per": float | None, "pbr": float | None}
        """
        return self._sector_averages_cache.get(sector, {"per": None, "pbr": None})
