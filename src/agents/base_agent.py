"""
Base Agent Abstract Class

모든 에이전트의 기반 클래스.
캐시 통합, 로깅, 공통 유틸리티를 제공합니다.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.data.cache import CacheManager


@dataclass
class BaseAgent(ABC):
    """
    에이전트 기반 추상 클래스

    모든 데이터 수집 및 분석 에이전트는 이 클래스를 상속해야 합니다.

    Attributes:
        cache: 캐시 매니저 인스턴스
        logger: 로거 인스턴스

    Abstract Methods:
        collect: 데이터 수집 메서드 (서브클래스에서 구현)

    사용 예시:
        class MarketDataAgent(BaseAgent):
            async def collect(self, symbols: list[str]) -> dict[str, Any]:
                # 구현
                pass

        agent = MarketDataAgent()
        data = await agent.collect(["005930", "000660"])
    """
    cache: CacheManager = field(default_factory=CacheManager)

    def __post_init__(self):
        """에이전트 초기화 후 로거 설정"""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def collect(self, symbols: List[str]) -> Dict[str, Any]:
        """
        데이터 수집 메서드

        서브클래스에서 반드시 구현해야 합니다.

        Args:
            symbols: 종목 코드 리스트

        Returns:
            종목코드를 키로 하는 데이터 딕셔너리
        """
        pass

    def _log_info(self, message: str) -> None:
        """정보 로그"""
        self.logger.info(message)

    def _log_warning(self, message: str) -> None:
        """경고 로그"""
        self.logger.warning(message)

    def _log_error(self, message: str) -> None:
        """에러 로그"""
        self.logger.error(message)

    def _log_debug(self, message: str) -> None:
        """디버그 로그"""
        self.logger.debug(message)

    def _get_cached_or_fetch(
        self,
        cache_key: str,
        fetch_func: callable,
        ttl_hours: int = 24,
        *args,
        **kwargs
    ) -> Optional[Any]:
        """
        캐시에서 데이터를 가져오거나 fetch_func를 호출하여 새로 가져옴

        Args:
            cache_key: 캐시 키
            fetch_func: 데이터 가져오기 함수
            ttl_hours: 캐시 TTL (시간)
            *args, **kwargs: fetch_func에 전달할 인자

        Returns:
            데이터 또는 None
        """
        # 캐시 확인
        cached = self.cache.get(cache_key, max_age_hours=ttl_hours)
        if cached is not None:
            self._log_debug(f"Cache hit: {cache_key}")
            return cached

        # 캐시 미스 시 데이터 가져오기
        self._log_debug(f"Cache miss: {cache_key}, fetching...")
        try:
            data = fetch_func(*args, **kwargs)
            if data is not None:
                self.cache.set(cache_key, data, ttl_hours=ttl_hours)
            return data
        except Exception as e:
            self._log_error(f"Failed to fetch data for {cache_key}: {e}")
            return None

    async def _get_cached_or_fetch_async(
        self,
        cache_key: str,
        fetch_func: callable,
        ttl_hours: int = 24,
        *args,
        **kwargs
    ) -> Optional[Any]:
        """
        비동기 버전의 캐시-또는-페치

        Args:
            cache_key: 캐시 키
            fetch_func: 비동기 데이터 가져오기 함수
            ttl_hours: 캐시 TTL (시간)
            *args, **kwargs: fetch_func에 전달할 인자

        Returns:
            데이터 또는 None
        """
        # 캐시 확인
        cached = self.cache.get(cache_key, max_age_hours=ttl_hours)
        if cached is not None:
            self._log_debug(f"Cache hit: {cache_key}")
            return cached

        # 캐시 미스 시 데이터 가져오기
        self._log_debug(f"Cache miss: {cache_key}, fetching...")
        try:
            data = await fetch_func(*args, **kwargs)
            if data is not None:
                self.cache.set(cache_key, data, ttl_hours=ttl_hours)
            return data
        except Exception as e:
            self._log_error(f"Failed to fetch data for {cache_key}: {e}")
            return None
