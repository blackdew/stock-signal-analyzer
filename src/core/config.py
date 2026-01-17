"""
Core Configuration Module

섹터 순환 투자 전략을 위한 핵심 설정 파일.
분석 대상 섹터, 루브릭 가중치, 투자 등급 기준 등을 정의합니다.
"""

import os
from typing import Dict, List, Tuple

# =============================================================================
# 분석 대상 섹터 및 대표 종목
# =============================================================================

SECTORS: Dict[str, List[str]] = {
    "반도체": ["005930", "000660", "042700"],  # 삼성전자, SK하이닉스, 한미반도체
    "조선": ["010140", "009540", "042660"],    # 삼성중공업, 한국조선해양, 대우조선해양
    # Phase 3에서 추가 예정:
    # "2차전지": ["373220", "006400", "051910"],
    # "자동차": ["005380", "000270", "012330"],
    # "바이오": ["207940", "068270", "035720"],
    # "금융": ["105560", "055550", "086790"],
}

# =============================================================================
# 루브릭 가중치 (기본값)
# =============================================================================

RUBRIC_WEIGHTS: Dict[str, int] = {
    "technical": 30,    # 기술적 분석 가중치
    "supply": 25,       # 수급 분석 가중치
    "fundamental": 25,  # 펀더멘털 분석 가중치
    "market": 20,       # 시장 환경 분석 가중치
}

# =============================================================================
# 투자 등급 기준
# =============================================================================

INVESTMENT_GRADES: Dict[str, Tuple[int, int]] = {
    "Strong Buy": (80, 100),   # 강력 매수
    "Buy": (60, 79),           # 매수
    "Hold": (40, 59),          # 보유/관망
    "Sell": (20, 39),          # 매도
    "Strong Sell": (0, 19),    # 강력 매도
}

# =============================================================================
# 캐시 설정
# =============================================================================

CACHE_EXPIRE_HOURS: int = 24
CACHE_DIR: str = "output/data/cache"

# =============================================================================
# API 설정
# =============================================================================

# 환경변수에서 API 키 로드
NEWS_API_KEY: str = os.environ.get("NEWS_API_KEY", "")
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")

# =============================================================================
# 유틸리티 함수
# =============================================================================

def get_grade_from_score(score: int) -> str:
    """
    점수를 기반으로 투자 등급을 반환합니다.

    Args:
        score: 0-100 사이의 점수

    Returns:
        투자 등급 문자열 (Strong Buy, Buy, Hold, Sell, Strong Sell)
    """
    for grade, (min_score, max_score) in INVESTMENT_GRADES.items():
        if min_score <= score <= max_score:
            return grade
    return "Hold"  # 기본값


def get_all_sector_symbols() -> List[str]:
    """
    모든 섹터의 종목 코드를 반환합니다.

    Returns:
        전체 종목 코드 리스트 (중복 제거)
    """
    all_symbols = []
    for symbols in SECTORS.values():
        all_symbols.extend(symbols)
    return list(set(all_symbols))


def get_sector_by_symbol(symbol: str) -> str:
    """
    종목 코드로 해당 섹터를 찾습니다.

    Args:
        symbol: 종목 코드

    Returns:
        섹터명 (찾지 못하면 "Unknown")
    """
    for sector, symbols in SECTORS.items():
        if symbol in symbols:
            return sector
    return "Unknown"
