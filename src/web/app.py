"""
FastAPI Application

FastAPI 애플리케이션 및 CORS 설정.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.web.routes.analysis import router as analysis_router
from src.web.routes.sectors import router as sectors_router
from src.web.routes.stocks import router as stocks_router
from src.web.schemas import HealthResponse


# =============================================================================
# 앱 상태 관리
# =============================================================================


class AppState:
    """애플리케이션 상태"""
    def __init__(self):
        # 비동기 분석 태스크 저장
        self.analysis_tasks: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """앱 라이프사이클 관리"""
    # 시작 시
    app.state.app_state = AppState()
    yield
    # 종료 시 (정리 작업)
    pass


# =============================================================================
# 앱 생성
# =============================================================================


def create_app(
    title: str = "투자 기회 분석 API",
    version: str = "1.0.0",
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """
    FastAPI 앱을 생성합니다.

    Args:
        title: API 제목
        version: API 버전
        cors_origins: 허용할 CORS 오리진 리스트

    Returns:
        FastAPI 앱
    """
    app = FastAPI(
        title=title,
        version=version,
        description="섹터 순환 투자 전략 분석 시스템 API",
        lifespan=lifespan,
    )

    # CORS 설정
    if cors_origins is None:
        cors_origins = [
            "http://localhost:3000",  # React 개발 서버
            "http://localhost:5173",  # Vite 개발 서버
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(analysis_router, prefix="/api", tags=["analysis"])
    app.include_router(sectors_router, prefix="/api", tags=["sectors"])
    app.include_router(stocks_router, prefix="/api", tags=["stocks"])

    # Health check 엔드포인트
    @app.get("/api/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """서버 상태 확인"""
        return HealthResponse(status="ok", version=version)

    return app


# 기본 앱 인스턴스 (uvicorn에서 직접 사용)
app = create_app()
