import pytest
from unittest.mock import MagicMock
import pandas as pd
import numpy as np

from src.core.rubric import RubricEngine, calc_trading_value_score
from src.agents.analysis.stock_analyzer import calculate_trading_guide, round_stock_tick, StockAnalysisResult
from src.agents.analysis.ranking_agent import RankingAgent

class DummyObject:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_round_stock_tick():
    """
    한국 주식 호가 단위(Tick size) 변환 헬퍼가 가격대별로 정확히 라운딩하는지 검증합니다.
    """
    # 1. 2000원 미만 (1원 단위)
    assert round_stock_tick(1543.2) == 1543
    # 2. 5000원 미만 (10원 단위로 안전 보정)
    assert round_stock_tick(3456.8) == 3460
    # 3. 20000원 미만 (10원 단위)
    assert round_stock_tick(12437) == 12440
    # 4. 50000원 미만 (50원 단위)
    assert round_stock_tick(35023) == 35000
    assert round_stock_tick(35028) == 35050
    # 5. 200000원 미만 (100원 단위)
    assert round_stock_tick(125430) == 125400
    # 6. 500000원 미만 (500원 단위)
    assert round_stock_tick(345280) == 345500
    # 7. 500000원 이상 (1000원 단위)
    assert round_stock_tick(754300) == 754000


def test_trading_guide_calculation():
    """
    ATR 및 ATR% 기반 1일 가격 매매 가이드가 매수 밴드 및 손절가, 목표가를 정확히 산출하는지 검증합니다.
    """
    # ATR 5000원, 현재가 100000원, Strong Buy(총점 85점)인 경우
    buy_low, buy_high, stop_loss, target_price = calculate_trading_guide(
        current_price=100000.0,
        atr=5000.0,
        atr_pct=None,
        total_score=85.0
    )
    # 주도주이므로 상한은 P - 0.2*A = 100000 - 1000 = 99000원
    # 하한은 P - 1.2*A = 100000 - 6000 = 94000원
    # 손절은 P - 2.0*A = 100000 - 10000 = 90000원
    # 목표는 P + 3.0*A = 100000 + 15000 = 115000원
    assert buy_high == 99000.0
    assert buy_low == 94000.0
    assert stop_loss == 90000.0
    assert target_price == 115000.0

    # 일반 종목(총점 50점), ATR 결측 상황(기본 3% 적용)인 경우
    # 3% 변동성: 10000 * 0.03 = 300원
    buy_low, buy_high, stop_loss, target_price = calculate_trading_guide(
        current_price=10000.0,
        atr=None,
        atr_pct=None,
        total_score=50.0
    )
    # 일반종목 상한: P - 0.5*A = 10000 - 150 = 9850원
    # 일반종목 하한: P - 1.5*A = 10000 - 450 = 9550원
    # 손절: P - 2.0*A = 10000 - 600 = 9400원
    # 목표: P + 3.0*A = 10000 + 900 = 10900원
    assert buy_high == 9850.0
    assert buy_low == 9550.0
    assert stop_loss == 9400.0
    assert target_price == 10900.0


def test_double_rescaling_with_missing_data():
    """
    일부 지표 및 카테고리가 통째로 결측인 상황에서 이중 리스케일링(H3 해결)이
    안정적으로 분모를 재조정하여 신뢰성 있는 총점을 반환하는지 검증합니다.
    """
    engine = RubricEngine(use_v3=True)
    
    # 1. 데이터가 거의 없는 극단적인 결측 상태
    market_data = DummyObject(
        current_price=10000.0,
        low_52w=8000.0,
        high_52w=12000.0,
        foreign_net_buy=[10.0, 20.0, -5.0, 10.0, 15.0],
        # 타 지표 대거 결측
    )
    
    # fundamental_data 및 news_data 전체 결측
    result = engine.calculate(
        symbol="005930",
        name="삼성전자",
        market_data=market_data,
        fundamental_data=None,
        news_data=None
    )
    
    # 전체 카테고리 중 일부(valuation, fundamental, shareholder 등)가 통째로 결측임에도
    # ZeroDivisionError 없이, 정상적인 총점(0~100)을 반환해야 함.
    assert 0.0 <= result.total_score <= 100.0
    assert result.rubric_version == "v3"


def test_ranking_scaling_patch():
    """
    RankingAgent가 Top 5를 선정할 때 V3 수급/펀더멘털의 15점 만점 기준(H4 해결)을
    정상적으로 100점 만점으로 정규화하여 가중 스코어를 반영하는지 검증합니다.
    """
    # StockAnalysisResult 가상 리스트 작성 (15점 만점인 V3 루브릭 결과가 들어있다고 가정)
    rubric_v3 = DummyObject(
        supply=DummyObject(max_score=15),
        fundamental=DummyObject(max_score=15)
    )
    
    stock_a = StockAnalysisResult(
        symbol="005930",
        name="삼성전자",
        sector="반도체",
        group="kospi_top10",
        market_cap=3000000,
        total_score=80.0,
        supply_score=15.0,        # 15점 만점에 15점 (100% 득점)
        fundamental_score=15.0,   # 15점 만점에 15점 (100% 득점)
        rubric_result=rubric_v3
    )
    
    stock_b = StockAnalysisResult(
        symbol="000660",
        name="SK하이닉스",
        sector="반도체",
        group="kospi_top10",
        market_cap=1000000,
        total_score=80.0,
        supply_score=7.5,         # 15점 만점에 7.5점 (50% 득점)
        fundamental_score=7.5,    # 15점 만점에 7.5점 (50% 득점)
        rubric_result=rubric_v3
    )
    
    agent = RankingAgent()
    
    # select_final_top5가 두 종목의 최종 점수를 올바르게 구별하는지 확인
    # stock_a의 환산 수급/펀더멘털 점수는 각각 100점이어야 하고, stock_b는 50점이어야 한다.
    # 최종점수 = total_score * 0.7 + supply_norm * 0.15 + fund_norm * 0.15
    # stock_a = 80 * 0.7 + 100 * 0.15 + 100 * 0.15 = 56 + 15 + 15 = 86점
    # stock_b = 80 * 0.7 + 50 * 0.15 + 50 * 0.15 = 56 + 7.5 + 7.5 = 71점
    
    top5 = agent.select_final_top5([stock_a, stock_b])
    
    assert top5[0].symbol == "005930"  # A가 더 높은 순위로 랭킹되어야 함
