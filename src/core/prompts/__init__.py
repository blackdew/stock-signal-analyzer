"""
Prompts Module

LLM 분석을 위한 프롬프트 템플릿을 제공합니다.
- stock_analysis: 개별 종목 분석 프롬프트
- sector_analysis: 섹터 분석 프롬프트
- schemas: JSON 출력 스키마
"""

from src.core.prompts.stock_analysis import (
    STOCK_ANALYSIS_PROMPT,
    build_stock_analysis_prompt,
)
from src.core.prompts.sector_analysis import (
    SECTOR_ANALYSIS_PROMPT,
    build_sector_analysis_prompt,
)
from src.core.prompts.schemas import (
    STOCK_SCORE_SCHEMA,
    SECTOR_SCORE_SCHEMA,
)

__all__ = [
    "STOCK_ANALYSIS_PROMPT",
    "build_stock_analysis_prompt",
    "SECTOR_ANALYSIS_PROMPT",
    "build_sector_analysis_prompt",
    "STOCK_SCORE_SCHEMA",
    "SECTOR_SCORE_SCHEMA",
]
