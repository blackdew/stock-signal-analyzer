"""
Fundamental Agent

재무제표 데이터를 수집하는 에이전트.
네이버 금융 크롤링을 통해 PER, PBR, ROE, 부채비율 등을 조회합니다.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from src.agents.base_agent import BaseAgent
from src.data.cache import CacheManager, CacheTTL
from src.data.fetcher import StockDataFetcher
from src.core.config import SECTORS, get_sector_by_symbol


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

    # 주주환원
    dividend_yield: Optional[float] = None  # 배당수익률 (%)

    # 업종 평균 (비교용)
    sector_avg_per: Optional[float] = None
    sector_avg_pbr: Optional[float] = None

    # [신규] 다개년 시계열 재무 정보 맵 (Piotroski F-Score, Value Band 계산용)
    yearly_history: Dict[str, List[float]] = field(default_factory=dict)


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
        self._log_debug(f"Collecting fundamental data for {len(symbols)} symbols")
        result: Dict[str, FundamentalData] = {}
        cache_hits = 0

        # 섹터 평균 사전 계산
        await self._calculate_sector_averages()

        total = len(symbols)
        for i, symbol in enumerate(symbols, 1):
            try:
                # 캐시 히트 체크
                cache_key = f"fundamental_{symbol}"
                if self.cache.get(cache_key, max_age_hours=CacheTTL.FUNDAMENTAL):
                    cache_hits += 1

                self._log_progress(i, total, f"Processing {symbol}")
                fundamental_data = await self._collect_single(symbol)
                if fundamental_data:
                    result[symbol] = fundamental_data
            except Exception as e:
                self._log_error(f"Failed to collect fundamental data for {symbol}: {e}")

        fetched = total - cache_hits
        self._log_debug(
            f"Collected fundamental data for {len(result)}/{total} symbols (cache: {cache_hits}, fetched: {fetched})"
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

        # 배당수익률 조회 (기존 fetcher 함수 활용)
        dividend_yield = self.fetcher.get_dividend_yield(symbol)

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
            dividend_yield=dividend_yield,
            sector_avg_per=sector_avg_per,
            sector_avg_pbr=sector_avg_pbr,
            yearly_history=financial_data.get("yearly_history", {}),
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
            "dividend_yield": fundamental_data.dividend_yield,
            "sector_avg_per": fundamental_data.sector_avg_per,
            "sector_avg_pbr": fundamental_data.sector_avg_pbr,
            "yearly_history": fundamental_data.yearly_history,
        }
        self.cache.set(cache_key, cache_data, ttl_hours=CacheTTL.FUNDAMENTAL)

        return fundamental_data

    def _fetch_financial_data(self, symbol: str) -> Dict[str, Any]:
        """
        재무 데이터를 가져옵니다. (네이버 금융 크롤링)

        Returns:
            재무 데이터 딕셔너리 (per, pbr, roe, debt_ratio, operating_margin, operating_profit_growth)
        """
        return self._fetch_from_naver(symbol)

    def _fetch_from_naver(self, symbol: str) -> Dict[str, Any]:
        """
        네이버 금융에서 펀더멘털 데이터를 크롤링합니다.

        크롤링 대상:
        - PER, PBR: em#_per, em#_pbr 태그
        - ROE, 부채비율, 영업이익률: 주요재무정보 테이블

        Returns:
            재무 데이터 딕셔너리
        """
        result: Dict[str, Any] = {}

        try:
            url = f"https://finance.naver.com/item/main.naver?code={symbol}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = response.apparent_encoding or "utf-8"

            if response.status_code != 200:
                self._log_warning(f"Naver finance request failed for {symbol}: {response.status_code}")
                return result

            soup = BeautifulSoup(response.text, "html.parser")

            # PER 추출 (em#_per)
            per_em = soup.select_one("em#_per")
            if per_em:
                try:
                    per_text = per_em.text.strip().replace(",", "")
                    if per_text and per_text != "N/A":
                        per_value = float(per_text)
                        if per_value > 0:
                            result["per"] = round(per_value, 2)
                except (ValueError, TypeError):
                    pass

            # PBR 추출 (em#_pbr)
            pbr_em = soup.select_one("em#_pbr")
            if pbr_em:
                try:
                    pbr_text = pbr_em.text.strip().replace(",", "")
                    if pbr_text and pbr_text != "N/A":
                        pbr_value = float(pbr_text)
                        if pbr_value > 0:
                            result["pbr"] = round(pbr_value, 2)
                except (ValueError, TypeError):
                    pass

            # 주요재무정보 테이블에서 ROE, 부채비율, 영업이익률 추출
            self._extract_financial_table_data(soup, result)

        except requests.RequestException as e:
            self._log_warning(f"Naver finance request error for {symbol}: {e}")
        except Exception as e:
            self._log_debug(f"Naver finance parsing failed for {symbol}: {e}")

        return result

    def _extract_financial_table_data(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """
        주요재무정보 테이블에서 최근 4개년 연간 실적 데이터를 시계열 리스트로 추출합니다.
        F-Score, PEG, Valuation Band 등에 실질적으로 연계됩니다.
        """
        result["yearly_history"] = {}
        
        # 재무 지표 매핑 딕셔너리
        metric_mapping = {
            "매출액": "revenue",
            "영업이익": "operating_profit",
            "당기순이익": "net_income",
            "영업이익률": "operating_margin",
            "ROE(지배주주)": "roe",
            "부채비율": "debt_ratio",
            "당좌비율": "current_ratio",  # 유동비율 대용
            "유동비율": "current_ratio",
            "자본금": "capital_stock",
            "영업활동현금흐름": "cfo",
            "자산총계": "assets",
        }

        def to_float(val_str: str) -> Optional[float]:
            try:
                val_str = val_str.strip().replace(",", "")
                if val_str and val_str not in ("-", "N/A", ""):
                    return float(val_str)
            except ValueError:
                pass
            return None

        for table in soup.select("table.tb_type1"):
            headers = [th.text.strip() for th in table.select("th")]
            if "ROE(지배주주)" not in headers:
                continue

            rows = table.select("tr")
            for row in rows:
                th = row.select_one("th")
                if not th:
                    continue

                th_text = th.text.strip()
                metric_key = None
                
                # 명칭 매칭
                for k, v in metric_mapping.items():
                    if k in th_text:
                        metric_key = v
                        break
                
                if not metric_key:
                    continue

                tds = row.select("td")
                if len(tds) < 4:
                    continue

                # 최근 연간 4개 칼럼 파싱 (보통 td의 0, 1, 2, 3 인덱스가 연간 실적)
                yearly_values = []
                for idx in range(4):
                    if idx < len(tds):
                        val = to_float(tds[idx].text)
                        yearly_values.append(val if val is not None else 0.0)  # 결측치는 안전하게 0.0 처리
                    else:
                        yearly_values.append(0.0)

                # 시계열에 축적
                result["yearly_history"][metric_key] = yearly_values

                # 단일 년도 대표값 (기존 루브릭 Fallback 호환성 유지)
                # 2024.12(인덱스 2) 또는 2023.12(인덱스 1) 데이터를 대표값으로 추출
                repr_val = None
                for idx in [2, 1]:
                    if idx < len(tds):
                        val = to_float(tds[idx].text)
                        if val is not None:
                            repr_val = val
                            break
                
                if repr_val is not None:
                    if metric_key == "roe" and "roe" not in result:
                        result["roe"] = round(repr_val, 2)
                    elif metric_key == "debt_ratio" and "debt_ratio" not in result:
                        result["debt_ratio"] = round(repr_val, 2)
                    elif metric_key == "operating_margin" and "operating_margin" not in result:
                        result["operating_margin"] = round(repr_val, 2)

            # 영업이익 성장률 YoY 자동 계산 (인덱스 1(전년) 대비 인덱스 2(당해)의 비율)
            if "operating_profit" in result["yearly_history"]:
                op_list = result["yearly_history"]["operating_profit"]
                if len(op_list) >= 3:
                    prev_op = op_list[1]
                    curr_op = op_list[2]
                    if prev_op != 0:
                        growth = ((curr_op - prev_op) / abs(prev_op)) * 100
                        result["operating_profit_growth"] = round(growth, 2)
                    else:
                        result["operating_profit_growth"] = 0.0

            # 매출액 성장률 YoY 자동 계산
            if "revenue" in result["yearly_history"]:
                rev_list = result["yearly_history"]["revenue"]
                if len(rev_list) >= 3:
                    prev_rev = rev_list[1]
                    curr_rev = rev_list[2]
                    if prev_rev != 0:
                        result["revenue_growth"] = round(((curr_rev - prev_rev) / abs(prev_rev)) * 100, 2)
                    else:
                        result["revenue_growth"] = 0.0
            break

    async def _calculate_sector_averages(self) -> None:
        """
        섹터별 평균 PER, PBR을 계산합니다.
        """
        if self._sector_averages_cache:
            return  # 이미 계산됨

        self._log_debug("Calculating sector averages...")

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

        self._log_debug(f"Calculated averages for {len(self._sector_averages_cache)} sectors")

    def get_sector_average(self, sector: str) -> Dict[str, Optional[float]]:
        """
        특정 섹터의 평균 밸류에이션을 반환합니다.

        Args:
            sector: 섹터명

        Returns:
            {"per": float | None, "pbr": float | None}
        """
        return self._sector_averages_cache.get(sector, {"per": None, "pbr": None})
