import pytest
from unittest.mock import MagicMock
from src.core.rubric import (
    calc_piotroski_f_score,
    calc_peg_ratio,
    calc_valuation_band_score
)

def test_piotroski_f_score_perfect():
    """
    [TDD 검증 1]
    9가지 건전성 기준(수익성, 재무건전성, 효율성)을 완전히 충족하는 시계열 데이터가 주어졌을 때
    F-Score가 정확히 9점 만점을 반환하는지 검증합니다.
    """
    # 9가지 조건을 완벽하게 만족하는 다개년 데이터 Mocking (길이 4로 맞춰 인덱스 1과 2 비교 작동 보장)
    history_data = {
        "roa": [0.0, 2.5, 5.0, 5.0],                  # 당기순이익/자산총계 (전년 2.5% -> 당해 5.0% 상승)
        "cfo": [0.0, 10.0, 15.0, 15.0],                # 영업활동현금흐름 (양수 및 지속 상승)
        "net_income": [0.0, 5.0, 8.0, 8.0],           # 당기순이익 (CFO 15.0 > 순이익 8.0으로 회계품질 우수)
        "debt_ratio": [0.0, 120.0, 90.0, 90.0],        # 부채비율 (전년 120% -> 당해 90%로 부채 감소)
        "current_ratio": [0.0, 150.0, 180.0, 180.0],    # 유동비율 (전년 150% -> 당해 180%로 유동성 개선)
        "capital_stock": [0.0, 500.0, 500.0, 500.0],    # 자본금 (신주 발행 없음, 500억 유지)
        "gross_margin": [0.0, 25.0, 30.0, 30.0],       # 매출총이익률 (전년 25% -> 당해 30%로 마진 개선)
        "operating_margin": [0.0, 10.0, 15.0, 15.0],   # 영업이익률 추가
        "revenue": [0.0, 1000.0, 1200.0, 1200.0],       # 매출액 추가
        "assets": [0.0, 10000.0, 10000.0, 10000.0],     # 자산총계 추가
        "asset_turnover": [0.0, 1.0, 1.2, 1.2],       # 총자산회전율 (전년 1.0회 -> 당해 1.2회로 운영 효율 상승)
    }
    
    score = calc_piotroski_f_score(history_data)
    assert score == 9, f"9가지 우량 조건을 통과했으나 {score}점이 산출되었습니다."

def test_piotroski_f_score_fallback():
    """
    [TDD 검증 2]
    일부 시계열 데이터가 누락(결측)되었을 때 ZeroDivisionError나 예외 없이
    안정적으로 안전한 폴백(기본 0점 혹은 평균 점수) 점수를 도출하는지 검증합니다.
    """
    empty_history = {}
    score = calc_piotroski_f_score(empty_history)
    assert score == 0, "결측 데이터 환경에서 기본 0점 폴백이 적용되지 않았습니다."
    
    partial_history = {
        "roa": [2.5, 5.0],
        # CFO 등 다른 시계열 항목 대량 누락
    }
    score_partial = calc_piotroski_f_score(partial_history)
    assert 0 <= score_partial <= 9, "일부 데이터만 존재할 때 범위 밖의 비정상 점수가 나왔습니다."

def test_peg_ratio_calculation():
    """
    [TDD 검증 3]
    PER = 10, 영업이익 성장률 = 20% 일 때 PEG = 0.5가 완벽하게 계산되고
    PEG 루브릭 기준에 맞춰 최고점(10점)을 획득하는지 검증합니다.
    """
    per = 10.0
    growth = 20.0
    
    score, peg_val = calc_peg_ratio(per, growth)
    assert peg_val == 0.5, f"PEG Ratio 계산이 잘못되었습니다: {peg_val} (기대치: 0.5)"
    assert score == 10.0, f"PEG가 0.5일 때 만점(10점)이 아닌 {score}점이 산출되었습니다."

def test_peg_ratio_clamping():
    """
    [TDD 검증 4]
    성장률이 0이거나 음수(역성장)일 때 분모가 0이 되어 발생하는 ZeroDivisionError나
    비정상 음수 점수 없이 Clamping(하한 클리핑)되어 기본 최소점(1점)을 반환하는지 검증합니다.
    """
    per = 15.0
    zero_growth = 0.0
    negative_growth = -15.0
    
    # 1. 0 성장률 검증
    score_zero, peg_zero = calc_peg_ratio(per, zero_growth)
    assert score_zero == 1.0, f"0 성장률일 때 안전 클리핑(1점)에 실패했습니다: {score_zero}점"
    
    # 2. 역성장 검증
    score_neg, peg_neg = calc_peg_ratio(per, negative_growth)
    assert score_neg == 1.0, f"역성장(-15%)일 때 최소 안전 점수(1점)에 실패했습니다: {score_neg}점"

def test_valuation_band_percentile():
    """
    [TDD 검증 5]
    현재 PBR이 5개년 역사적 고가(2.0)와 저가(1.0) 사이 중 바닥권(1.1)에 머무를 때
    역사적 저점 분위수(10%)를 올바르게 계산하여 높은 루브릭 점수(9점 이상)를 주는지 검증합니다.
    """
    current_pbr = 1.1
    pbr_5y_min = 1.0
    pbr_5y_max = 2.0
    
    score = calc_valuation_band_score(current_pbr, pbr_5y_min, pbr_5y_max)
    assert score >= 9.0, f"역사적 10% 최저 바닥권 PBR임에도 낮은 루브릭 점수({score}점)가 산출되었습니다."
