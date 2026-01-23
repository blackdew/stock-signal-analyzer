"""
Routes Package

API 라우터 모듈.
"""

from src.web.routes.analysis import router as analysis_router
from src.web.routes.sectors import router as sectors_router
from src.web.routes.stocks import router as stocks_router

__all__ = ["analysis_router", "sectors_router", "stocks_router"]
