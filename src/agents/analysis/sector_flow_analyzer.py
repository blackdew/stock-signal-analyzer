"""
Sector Flow Analyzer

섹터별 상대순환그래프(RRG) 좌표 및 자금 흐름(Money Flow) 점수를 산출하는 분석기.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.agents.base_agent import BaseAgent
from src.core.config import SECTORS


# =============================================================================
# 1. 퀀트 RRG 및 자금 흐름 연산 함수군
# =============================================================================

def get_rrg_quadrant(x: float, y: float) -> str:
    """
    RRG 좌표값에 따라 4대 국면(분면) 판정
    
    경계값 100.0 기준 Strict하게 분류하여 데이터 미충족 시 중립 좌표(100.0, 100.0)가 
    안정적으로 Lagging/Improving 국면에 매핑되도록 처리합니다.
    """
    if x > 100.0 and y > 100.0:
        return "Leading"
    elif x > 100.0 and y <= 100.0:
        return "Weakening"
    elif x <= 100.0 and y <= 100.0:
        return "Lagging"
    else:
        return "Improving"


def calc_rrg_coordinates(
    sector_prices: List[float],
    benchmark_prices: List[float]
) -> Tuple[float, float]:
    """
    상대순환그래프(RRG) Z-Score 좌표 계산 (평균 100, 표준편차 1 기준 스케일)
    
    RS Ratio와 RS Momentum의 Z-Score를 100 기준 좌표로 스케일 변환합니다.
    """
    # 20거래일 시계열 조건 미충족 시 낙오/개선 중립 영역으로 안전한 Fallback 보장
    if not sector_prices or not benchmark_prices or len(sector_prices) < 20 or len(benchmark_prices) < 20:
        return 100.0, 100.0

    try:
        # 데이터 길이 정렬
        min_len = min(len(sector_prices), len(benchmark_prices))
        sec_p = sector_prices[-min_len:]
        bench_p = benchmark_prices[-min_len:]

        # 1. RS Ratio 산출
        rs_ratios = []
        for sp, bp in zip(sec_p, bench_p):
            if bp <= 0:
                rs_ratios.append(100.0)
            else:
                rs_ratios.append((sp / bp) * 100.0)

        # RS Ratio Z-Score
        rs_mean = np.mean(rs_ratios)
        rs_std = np.std(rs_ratios)
        rs_z = (rs_ratios[-1] - rs_mean) / rs_std if rs_std > 0 else 0.0

        # 2. RS Momentum 산출
        rs_moms = []
        for i in range(1, len(rs_ratios)):
            prev = rs_ratios[i-1]
            if prev <= 0:
                rs_moms.append(100.0)
            else:
                rs_moms.append((rs_ratios[i] / prev) * 100.0)

        # RS Momentum Z-Score
        mom_mean = np.mean(rs_moms)
        mom_std = np.std(rs_moms)
        mom_z = (rs_moms[-1] - mom_mean) / mom_std if mom_std > 0 else 0.0

        # 3. Z-Score 스케일 변환 (평균 100, 표준편차 1)
        x_coord = round(100.0 + rs_z, 2)
        y_coord = round(100.0 + mom_z, 2)

        return x_coord, y_coord

    except Exception:
        return 100.0, 100.0


def calc_sector_money_flow_score(
    sector_volumes: List[float],
    market_volumes: List[float],
    net_buy: float,
    market_cap: float
) -> float:
    """
    섹터 자금 흐름 점수 산출 (100점 만점)
    
    - 거래대금 회전율 지표 (40점 만점)
    - 기관/외인 수급 강도 지표 (60점 만점)
    
    0 또는 음수 조건 하에서도 분모 ZeroDivisionError 및 음수 점수가 발생하지 않도록
    안전한 클리핑(Clamping) 처리가 장착되어 있습니다.
    """
    if not sector_volumes or len(sector_volumes) == 0:
        return 5.0

    try:
        # 1. 거래대금 회전율 지표 (40점 만점)
        vol_today = sector_volumes[-1]
        
        # 극단적 0 거래대금일 때 즉시 최소 점수(5점) 클리핑 적용
        if vol_today <= 0:
            volume_score = 5.0
        else:
            vol_avg = np.mean(sector_volumes) if len(sector_volumes) > 0 else 0.0
            
            if vol_avg <= 0:
                vol_ratio = 1.0
            else:
                vol_ratio = vol_today / vol_avg

            # 거래 회전 비율에 따른 40점 만점 환산
            if vol_ratio >= 2.0:
                volume_score = 40.0
            elif vol_ratio >= 1.5:
                volume_score = 35.0
            elif vol_ratio >= 1.0:
                volume_score = 30.0
            elif vol_ratio >= 0.5:
                volume_score = 20.0
            else:
                volume_score = 10.0

        # 2. 수급 강도 지표 (60점 만점)
        if market_cap <= 0:
            buy_score = 30.0
        else:
            # 수급 비중 %
            buy_ratio = (net_buy / market_cap) * 100.0
            
            if buy_ratio >= 3.0:
                buy_score = 60.0
            elif buy_ratio >= 1.0:
                buy_score = 50.0
            elif buy_ratio >= 0.0:
                buy_score = 40.0
            elif buy_ratio >= -1.0:
                buy_score = 20.0
            else:
                buy_score = 5.0

        total_score = volume_score + buy_score
        return round(max(0.0, min(100.0, total_score)), 2)

    except Exception:
        return 5.0


# =============================================================================
# 2. SectorFlowAnalyzer Agent 클래스
# =============================================================================

@dataclass
class SectorFlowResult:
    """섹터 자금 흐름 분석 단일 결과"""
    sector_name: str
    rrg_x: float
    rrg_y: float
    quadrant: str
    money_flow_score: float
    rank: int = 0


@dataclass
class SectorFlowAnalyzer(BaseAgent):
    """
    섹터 상대순환 및 자금 흐름 모니터링 에이전트
    """

    async def collect(self, symbols: List[str]) -> Dict[str, Any]:
        """
        BaseAgent 인터페이스 구현.
        """
        return {}

    async def analyze_flow(
        self,
        sector_data_map: Dict[str, Dict[str, Any]]
    ) -> List[SectorFlowResult]:
        """
        수집된 섹터 시계열 원본 데이터를 바탕으로 RRG 및 Money Flow Score 산출
        """
        results: List[SectorFlowResult] = []
        
        # 벤치마크 지수 설정 (여기서는 간단히 각 섹터 가격 지수의 평균값을 구해서 사용)
        all_sector_prices = []
        for name, data in sector_data_map.items():
            prices = data.get("prices", [])
            if prices:
                all_sector_prices.append(prices)
                
        benchmark_prices = []
        if all_sector_prices:
            min_len = min(len(p) for p in all_sector_prices)
            for i in range(min_len):
                avg_val = np.mean([p[i] for p in all_sector_prices])
                benchmark_prices.append(avg_val)
        else:
            # 벤치마크 부재 시 임시 플랫 지수
            benchmark_prices = [100.0] * 20

        for sector_name, data in sector_data_map.items():
            prices = data.get("prices", [])
            volumes = data.get("volumes", [])
            market_volumes = data.get("market_volumes", [])
            net_buy = data.get("net_buy", 0.0)
            market_cap = data.get("market_cap", 1000.0)

            # RRG 연산
            x, y = calc_rrg_coordinates(prices, benchmark_prices)
            quadrant = get_rrg_quadrant(x, y)

            # 자금 흐름 점수 연산
            flow_score = calc_sector_money_flow_score(
                sector_volumes=volumes,
                market_volumes=market_volumes,
                net_buy=net_buy,
                market_cap=market_cap
            )

            results.append(SectorFlowResult(
                sector_name=sector_name,
                rrg_x=x,
                rrg_y=y,
                quadrant=quadrant,
                money_flow_score=flow_score
            ))

        # 자금 흐름 스코어 기준 순위 매기기
        results.sort(key=lambda r: r.money_flow_score, reverse=True)
        for i, res in enumerate(results, 1):
            res.rank = i

        return results
