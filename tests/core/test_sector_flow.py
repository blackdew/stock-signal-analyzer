import pytest
from typing import Dict, List
import numpy as np

# 우리가 개발할 sector_flow_analyzer 모듈에서 함수들을 임포트할 예정입니다.
from src.agents.analysis.sector_flow_analyzer import (
    calc_rrg_coordinates,
    calc_sector_money_flow_score,
    get_rrg_quadrant
)

def test_rrg_quadrant_classification():
    """
    [TDD 검증 1]
    RS Z-Score와 Momentum Z-Score 좌표값에 따라 RRG 4대 국면(분면) 판정이
    정확히 매칭되는지 검증합니다.
    - X >= 100, Y >= 100: Leading (주도)
    - X >= 100, Y < 100: Weakening (약화)
    - X < 100, Y < 100: Lagging (낙오)
    - X < 100, Y >= 100: Improving (개선)
    """
    assert get_rrg_quadrant(101.5, 100.2) == "Leading"
    assert get_rrg_quadrant(100.8, 99.1) == "Weakening"
    assert get_rrg_quadrant(98.5, 97.2) == "Lagging"
    assert get_rrg_quadrant(99.1, 102.3) == "Improving"

def test_rrg_calculation_perfect():
    """
    [TDD 검증 2]
    벤치마크 대비 섹터 가격 지수가 가속 상승세를 탈 때
    RRG X, Y 좌표(Z-Score 100 기준 스케일)가 100점 이상(Leading) 영역으로
    올바르게 수렴되는지 검증합니다.
    """
    # 전일 대비 상승 비율(Momentum) 자체가 가속적으로 폭증하는 시계열 대입
    # 복리로 가속 매집되는 퀀트 모멘텀을 모델링
    sector_prices = [100.0 * ((1.01 + 0.003 * i) ** i) for i in range(25)]
    benchmark_prices = [100.0 for _ in range(25)]
    
    # 4분면 계산
    x_coord, y_coord = calc_rrg_coordinates(sector_prices, benchmark_prices)
    
    assert x_coord > 100.0, f"상승세 섹터의 RS Ratio({x_coord})가 100 이하입니다."
    assert y_coord > 100.0, f"상승세 섹터의 RS Momentum({y_coord})이 100 이하입니다."
    assert get_rrg_quadrant(x_coord, y_coord) == "Leading"

def test_rrg_fallback_on_missing_data():
    """
    [TDD 검증 3]
    가격 시계열 개수가 부족하거나(20일 미만) 결측치가 포함되어 있을 때
    에러 없이 기본 중립값(100.0, 100.0, 'Lagging/Improving 중립')을 안정적으로 도출하는지 검증합니다.
    """
    empty_prices: List[float] = []
    bench_prices: List[float] = []
    
    x, y = calc_rrg_coordinates(empty_prices, bench_prices)
    assert x == 100.0
    assert y == 100.0
    assert get_rrg_quadrant(x, y) in ("Weakening", "Lagging") # 중립 판정 영역

def test_sector_money_flow_score():
    """
    [TDD 검증 4]
    섹터 거래대금 유입이 5일 평균 대비 크게 증가하고(예: 2배),
    외인/기관 누적 순매수도 큰 규모의 양수일 때
    Money Flow Score가 고득점(80점 이상)을 획득하는지 검증합니다.
    """
    # 거래대금: 5일간 평균 100억인데 당일 250억 (대폭 증가)
    sector_volume_history = [100.0, 100.0, 100.0, 100.0, 250.0]
    market_volume_history = [1000.0, 1000.0, 1000.0, 1000.0, 2000.0]
    
    # 누적 수급: 외국인 + 기관 순매수 50억 (시가총액 1000억 대비 5%)
    net_buy_amount = 50.0
    sector_market_cap = 1000.0
    
    score = calc_sector_money_flow_score(
        sector_volumes=sector_volume_history,
        market_volumes=market_volume_history,
        net_buy=net_buy_amount,
        market_cap=sector_market_cap
    )
    
    assert score >= 80.0, f"자금 유입 및 수급 폭발 조건임에도 낮은 점수({score})가 산출되었습니다."

def test_money_flow_clamping_and_fallback():
    """
    [TDD 검증 5]
    거래대금이 0이거나 역성장(수급 음수)인 극단적 상태에서도
    ZeroDivisionError 없이 안전하게 최하점(0~10점 사이)으로 하한 클리핑을 보장하는지 검증합니다.
    """
    zero_volumes = [0.0, 0.0, 0.0, 0.0, 0.0]
    market_volumes = [1000.0, 1000.0, 1000.0, 1000.0, 1000.0]
    
    # 음수 수급
    negative_net_buy = -100.0
    sector_market_cap = 1000.0
    
    score = calc_sector_money_flow_score(
        sector_volumes=zero_volumes,
        market_volumes=market_volumes,
        net_buy=negative_net_buy,
        market_cap=sector_market_cap
    )
    
    assert 0.0 <= score <= 10.0, f"극단적 역성장/0 거래량 상태에서 클리핑에 실패했습니다: {score}점"
