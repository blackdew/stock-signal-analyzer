"""
Cache Manager Module

JSON 파일 기반 캐싱 시스템.
데이터 유형별 TTL(Time-To-Live) 관리 및 패턴 매칭 삭제를 지원합니다.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
import hashlib


@dataclass
class CacheEntry:
    """캐시 항목"""
    data: Any
    created_at: str  # ISO format
    expires_at: str  # ISO format


@dataclass
class CacheManager:
    """
    JSON 파일 기반 캐시 매니저

    캐시 만료 정책:
    - 주가/거래량: 장 마감 후 갱신 (기본 4시간, 장중에는 유효)
    - 시총 순위: 24시간
    - 수급 데이터: 24시간
    - 재무제표: 7일 (168시간)

    사용 예시:
        cache = CacheManager()

        # 캐시 저장
        cache.set("market_cap_005930", data, ttl_hours=24)

        # 캐시 조회
        data = cache.get("market_cap_005930", max_age_hours=24)

        # 패턴 매칭 삭제
        deleted = cache.clear("market_cap_*")
    """
    cache_dir: Path = field(default_factory=lambda: Path("output/data/cache"))

    def __post_init__(self):
        """캐시 디렉토리 생성"""
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_cache_path(self, key: str) -> Path:
        """
        캐시 키를 파일 경로로 변환

        긴 키나 특수문자가 포함된 키는 해시로 변환합니다.
        """
        # 안전한 파일명으로 변환
        safe_key = "".join(c if c.isalnum() or c in "_-" else "_" for c in key)

        # 너무 긴 경우 해시 사용
        if len(safe_key) > 100:
            safe_key = hashlib.md5(key.encode()).hexdigest()

        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str, max_age_hours: int = 24) -> Optional[Any]:
        """
        캐시 조회

        Args:
            key: 캐시 키
            max_age_hours: 최대 허용 나이 (시간). 이보다 오래된 캐시는 None 반환

        Returns:
            캐시된 데이터 또는 None (캐시 미스 또는 만료)
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self.logger.debug(f"Cache miss: {key} (file not found)")
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                entry_data = json.load(f)

            entry = CacheEntry(**entry_data)
            created_at = datetime.fromisoformat(entry.created_at)
            expires_at = datetime.fromisoformat(entry.expires_at)
            now = datetime.now()

            # 만료 확인 (저장 시 설정된 TTL 또는 요청된 max_age 중 더 엄격한 조건)
            if now > expires_at:
                self.logger.debug(f"Cache expired: {key} (expired at {expires_at})")
                return None

            age = now - created_at
            if age > timedelta(hours=max_age_hours):
                self.logger.debug(f"Cache too old: {key} (age: {age}, max: {max_age_hours}h)")
                return None

            self.logger.debug(f"Cache hit: {key} (age: {age})")
            return entry.data

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Cache read error for {key}: {e}")
            # 손상된 캐시 파일 삭제
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, key: str, value: Any, ttl_hours: int = 24) -> None:
        """
        캐시 저장

        Args:
            key: 캐시 키
            value: 저장할 데이터 (JSON 직렬화 가능해야 함)
            ttl_hours: Time-To-Live (시간)
        """
        cache_path = self._get_cache_path(key)

        now = datetime.now()
        entry = CacheEntry(
            data=value,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(hours=ttl_hours)).isoformat()
        )

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({
                    "data": entry.data,
                    "created_at": entry.created_at,
                    "expires_at": entry.expires_at
                }, f, ensure_ascii=False, indent=2, default=str)

            self.logger.debug(f"Cache set: {key} (TTL: {ttl_hours}h)")

        except (TypeError, ValueError) as e:
            self.logger.error(f"Cache write error for {key}: {e}")

    def clear(self, pattern: str = "*") -> int:
        """
        패턴 매칭 캐시 삭제

        Args:
            pattern: glob 패턴 (예: "market_*", "*", "fundamental_005930")

        Returns:
            삭제된 캐시 파일 개수
        """
        deleted_count = 0

        # "*"는 모든 파일 삭제
        if pattern == "*":
            glob_pattern = "*.json"
        else:
            # 패턴을 안전한 파일명으로 변환하여 glob 사용
            safe_pattern = "".join(c if c.isalnum() or c in "_-*?" else "_" for c in pattern)
            glob_pattern = f"{safe_pattern}.json"

        for cache_file in self.cache_dir.glob(glob_pattern):
            try:
                cache_file.unlink()
                deleted_count += 1
                self.logger.debug(f"Cache deleted: {cache_file.name}")
            except OSError as e:
                self.logger.warning(f"Failed to delete cache {cache_file}: {e}")

        self.logger.info(f"Cleared {deleted_count} cache entries matching '{pattern}'")
        return deleted_count

    def is_valid(self, key: str, max_age_hours: int = 24) -> bool:
        """
        캐시 유효성 확인 (데이터를 로드하지 않고)

        Args:
            key: 캐시 키
            max_age_hours: 최대 허용 나이 (시간)

        Returns:
            캐시가 유효하면 True
        """
        return self.get(key, max_age_hours) is not None

    def get_stats(self) -> dict:
        """
        캐시 통계 반환

        Returns:
            {
                "total_entries": int,
                "total_size_kb": float,
                "oldest_entry": str | None,
                "newest_entry": str | None
            }
        """
        cache_files = list(self.cache_dir.glob("*.json"))

        if not cache_files:
            return {
                "total_entries": 0,
                "total_size_kb": 0.0,
                "oldest_entry": None,
                "newest_entry": None
            }

        total_size = sum(f.stat().st_size for f in cache_files)
        mtimes = [(f, f.stat().st_mtime) for f in cache_files]
        oldest = min(mtimes, key=lambda x: x[1])
        newest = max(mtimes, key=lambda x: x[1])

        return {
            "total_entries": len(cache_files),
            "total_size_kb": round(total_size / 1024, 2),
            "oldest_entry": oldest[0].stem,
            "newest_entry": newest[0].stem
        }


# 캐시 TTL 상수 (시간 단위)
class CacheTTL:
    """캐시 만료 시간 상수"""
    PRICE = 4           # 주가/거래량: 장중 4시간 (장 마감 후 갱신)
    MARKET_CAP = 24     # 시총 순위: 24시간
    SUPPLY = 24         # 수급 데이터: 24시간
    FUNDAMENTAL = 168   # 재무제표: 7일
