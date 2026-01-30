"""
JSON Output Schemas

LLM 응답의 JSON 스키마 정의.
V3 8대 핵심 루브릭을 지원합니다.
"""

from typing import Any, Dict, List, TypedDict


# =============================================================================
# Stock Score Schema (V3 8대 핵심 루브릭)
# =============================================================================

class CategoryScoreSchema(TypedDict):
    """카테고리별 점수 스키마"""
    score: float
    reasoning: str


class CategoriesSchemaV3(TypedDict):
    """V3 8대 핵심 루브릭 스키마"""
    valuation: CategoryScoreSchema      # 밸류에이션 (20점)
    fundamental: CategoryScoreSchema    # 펀더멘털 (15점)
    supply: CategoryScoreSchema         # 수급 (15점)
    momentum: CategoryScoreSchema       # 모멘텀 (15점)
    technical: CategoryScoreSchema      # 기술적 (10점)
    sector: CategoryScoreSchema         # 섹터 (10점)
    risk: CategoryScoreSchema           # 리스크 (10점)
    shareholder: CategoryScoreSchema    # 주주환원 (5점)


class StockScoreSchemaV3(TypedDict):
    """종목 점수 응답 스키마 (V3)"""
    total_score: float
    grade: str
    categories: CategoriesSchemaV3
    summary: str
    financial_analysis: str
    technical_analysis: str
    market_sentiment: str
    comprehensive_analysis: str
    investment_thesis: List[str]
    risks: List[str]


# 하위 호환성을 위한 V2 스키마 (deprecated)
class CategoriesSchema(TypedDict):
    """전체 카테고리 스키마 (V2, deprecated)"""
    technical: CategoryScoreSchema
    supply: CategoryScoreSchema
    fundamental: CategoryScoreSchema
    market: CategoryScoreSchema
    risk: CategoryScoreSchema
    relative_strength: CategoryScoreSchema


class StockScoreSchema(TypedDict):
    """종목 점수 응답 스키마 (V2, deprecated)"""
    total_score: float
    grade: str
    categories: CategoriesSchema
    summary: str
    financial_analysis: str
    technical_analysis: str
    market_sentiment: str
    comprehensive_analysis: str
    investment_thesis: List[str]
    risks: List[str]


# =============================================================================
# Sector Score Schema
# =============================================================================

class SectorScoreSchema(TypedDict):
    """섹터 점수 응답 스키마"""
    reasoning: str
    outlook: str
    key_drivers: List[str]
    investment_strategy: str


# =============================================================================
# Schema Definitions (for validation)
# =============================================================================

# V3 8대 핵심 루브릭 스키마
STOCK_SCORE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": [
        "total_score", "grade", "categories", "summary",
        "financial_analysis", "technical_analysis", "market_sentiment",
        "comprehensive_analysis", "investment_thesis", "risks"
    ],
    "properties": {
        "total_score": {"type": "number", "minimum": 0, "maximum": 100},
        "grade": {
            "type": "string",
            "enum": ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]
        },
        "categories": {
            "type": "object",
            "required": ["valuation", "fundamental", "supply", "momentum", "technical", "sector", "risk", "shareholder"],
            "properties": {
                "valuation": {
                    "type": "object",
                    "required": ["score", "reasoning"],
                    "properties": {
                        "score": {"type": "number", "minimum": 0, "maximum": 20},
                        "reasoning": {"type": "string"}
                    }
                },
                "fundamental": {
                    "type": "object",
                    "required": ["score", "reasoning"],
                    "properties": {
                        "score": {"type": "number", "minimum": 0, "maximum": 15},
                        "reasoning": {"type": "string"}
                    }
                },
                "supply": {
                    "type": "object",
                    "required": ["score", "reasoning"],
                    "properties": {
                        "score": {"type": "number", "minimum": 0, "maximum": 15},
                        "reasoning": {"type": "string"}
                    }
                },
                "momentum": {
                    "type": "object",
                    "required": ["score", "reasoning"],
                    "properties": {
                        "score": {"type": "number", "minimum": 0, "maximum": 15},
                        "reasoning": {"type": "string"}
                    }
                },
                "technical": {
                    "type": "object",
                    "required": ["score", "reasoning"],
                    "properties": {
                        "score": {"type": "number", "minimum": 0, "maximum": 10},
                        "reasoning": {"type": "string"}
                    }
                },
                "sector": {
                    "type": "object",
                    "required": ["score", "reasoning"],
                    "properties": {
                        "score": {"type": "number", "minimum": 0, "maximum": 10},
                        "reasoning": {"type": "string"}
                    }
                },
                "risk": {
                    "type": "object",
                    "required": ["score", "reasoning"],
                    "properties": {
                        "score": {"type": "number", "minimum": 0, "maximum": 10},
                        "reasoning": {"type": "string"}
                    }
                },
                "shareholder": {
                    "type": "object",
                    "required": ["score", "reasoning"],
                    "properties": {
                        "score": {"type": "number", "minimum": 0, "maximum": 5},
                        "reasoning": {"type": "string"}
                    }
                }
            }
        },
        "summary": {"type": "string"},
        "financial_analysis": {"type": "string"},
        "technical_analysis": {"type": "string"},
        "market_sentiment": {"type": "string"},
        "comprehensive_analysis": {"type": "string"},
        "investment_thesis": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 4
        }
    }
}


SECTOR_SCORE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["reasoning", "outlook", "key_drivers", "investment_strategy"],
    "properties": {
        "reasoning": {"type": "string"},
        "outlook": {"type": "string"},
        "key_drivers": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5
        },
        "investment_strategy": {"type": "string"}
    }
}


def validate_stock_score(data: Dict[str, Any]) -> bool:
    """
    종목 점수 응답을 검증합니다 (V3 8대 루브릭).

    Args:
        data: LLM 응답 JSON

    Returns:
        검증 성공 여부
    """
    try:
        # 필수 필드 확인
        required_fields = [
            "total_score", "grade", "categories", "summary",
            "financial_analysis", "technical_analysis", "market_sentiment",
            "comprehensive_analysis", "investment_thesis", "risks"
        ]
        for field in required_fields:
            if field not in data:
                return False

        # 점수 범위 확인
        if not (0 <= data["total_score"] <= 100):
            return False

        # 등급 확인
        valid_grades = ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]
        if data["grade"] not in valid_grades:
            return False

        # V3 카테고리 확인
        categories = data.get("categories", {})
        required_categories = ["valuation", "fundamental", "supply", "momentum", "technical", "sector", "risk", "shareholder"]
        for cat in required_categories:
            if cat not in categories:
                return False
            if "score" not in categories[cat] or "reasoning" not in categories[cat]:
                return False

        return True

    except Exception:
        return False


def validate_sector_score(data: Dict[str, Any]) -> bool:
    """
    섹터 점수 응답을 검증합니다.

    Args:
        data: LLM 응답 JSON

    Returns:
        검증 성공 여부
    """
    try:
        required_fields = ["reasoning", "outlook", "key_drivers", "investment_strategy"]
        for field in required_fields:
            if field not in data:
                return False

        if not isinstance(data["key_drivers"], list):
            return False

        return True

    except Exception:
        return False
