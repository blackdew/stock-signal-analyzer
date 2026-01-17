"""
CacheManager 테스트

캐시 저장, 조회, 만료, 삭제 기능을 테스트합니다.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.data.cache import CacheManager, CacheTTL


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_cache_dir():
    """임시 캐시 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache(temp_cache_dir):
    """CacheManager 인스턴스"""
    return CacheManager(cache_dir=temp_cache_dir)


# =============================================================================
# 기본 동작 테스트
# =============================================================================


def test_cache_init(cache, temp_cache_dir):
    """캐시 초기화 테스트"""
    assert cache.cache_dir == temp_cache_dir
    assert cache.cache_dir.exists()


def test_cache_set_and_get(cache):
    """캐시 저장 및 조회 테스트"""
    cache.set("test_key", {"value": 123}, ttl_hours=24)
    result = cache.get("test_key", max_age_hours=24)

    assert result is not None
    assert result["value"] == 123


def test_cache_miss(cache):
    """캐시 미스 테스트"""
    result = cache.get("nonexistent_key")
    assert result is None


def test_cache_overwrite(cache):
    """캐시 덮어쓰기 테스트"""
    cache.set("key", {"v": 1})
    cache.set("key", {"v": 2})

    result = cache.get("key")
    assert result["v"] == 2


# =============================================================================
# 만료 테스트
# =============================================================================


def test_cache_expired(cache, temp_cache_dir):
    """만료된 캐시 테스트"""
    # 직접 만료된 캐시 파일 생성
    cache_path = temp_cache_dir / "expired_key.json"
    expired_time = datetime.now() - timedelta(hours=2)

    cache_data = {
        "data": {"value": 123},
        "created_at": expired_time.isoformat(),
        "expires_at": (expired_time + timedelta(hours=1)).isoformat(),  # 1시간 전 만료
    }

    with open(cache_path, "w") as f:
        json.dump(cache_data, f)

    # 조회 시 None 반환
    result = cache.get("expired_key", max_age_hours=24)
    assert result is None


def test_cache_max_age_exceeded(cache, temp_cache_dir):
    """max_age 초과 테스트"""
    # 3시간 전 생성된 캐시
    cache_path = temp_cache_dir / "old_key.json"
    old_time = datetime.now() - timedelta(hours=3)

    cache_data = {
        "data": {"value": 123},
        "created_at": old_time.isoformat(),
        "expires_at": (old_time + timedelta(hours=24)).isoformat(),  # TTL은 아직 유효
    }

    with open(cache_path, "w") as f:
        json.dump(cache_data, f)

    # max_age가 2시간이면 None 반환
    result = cache.get("old_key", max_age_hours=2)
    assert result is None

    # max_age가 4시간이면 데이터 반환
    result = cache.get("old_key", max_age_hours=4)
    assert result is not None


# =============================================================================
# 삭제 테스트
# =============================================================================


def test_cache_clear_all(cache):
    """전체 캐시 삭제 테스트"""
    cache.set("key1", {"v": 1})
    cache.set("key2", {"v": 2})
    cache.set("key3", {"v": 3})

    deleted = cache.clear("*")

    assert deleted == 3
    assert cache.get("key1") is None
    assert cache.get("key2") is None
    assert cache.get("key3") is None


def test_cache_clear_pattern(cache):
    """패턴 매칭 삭제 테스트"""
    cache.set("market_005930", {"v": 1})
    cache.set("market_000660", {"v": 2})
    cache.set("fundamental_005930", {"v": 3})

    deleted = cache.clear("market_*")

    assert deleted == 2
    assert cache.get("market_005930") is None
    assert cache.get("market_000660") is None
    assert cache.get("fundamental_005930") is not None


def test_cache_clear_specific(cache):
    """특정 키 삭제 테스트"""
    cache.set("target", {"v": 1})
    cache.set("other", {"v": 2})

    deleted = cache.clear("target")

    assert deleted == 1
    assert cache.get("target") is None
    assert cache.get("other") is not None


# =============================================================================
# 유효성 검사 테스트
# =============================================================================


def test_cache_is_valid(cache):
    """캐시 유효성 검사 테스트"""
    cache.set("valid_key", {"v": 1}, ttl_hours=24)

    assert cache.is_valid("valid_key", max_age_hours=24) is True
    assert cache.is_valid("nonexistent", max_age_hours=24) is False


# =============================================================================
# 통계 테스트
# =============================================================================


def test_cache_stats_empty(cache):
    """빈 캐시 통계 테스트"""
    stats = cache.get_stats()

    assert stats["total_entries"] == 0
    assert stats["total_size_kb"] == 0.0
    assert stats["oldest_entry"] is None
    assert stats["newest_entry"] is None


def test_cache_stats_with_data(cache):
    """데이터가 있는 캐시 통계 테스트"""
    cache.set("key1", {"v": 1})
    cache.set("key2", {"v": 2})

    stats = cache.get_stats()

    assert stats["total_entries"] == 2
    assert stats["total_size_kb"] > 0
    assert stats["oldest_entry"] is not None
    assert stats["newest_entry"] is not None


# =============================================================================
# 엣지 케이스 테스트
# =============================================================================


def test_cache_special_characters_in_key(cache):
    """특수문자가 포함된 키 테스트"""
    cache.set("market:005930/data", {"v": 1})
    result = cache.get("market:005930/data")
    assert result is not None


def test_cache_long_key(cache):
    """긴 키 테스트 (해시 사용)"""
    long_key = "a" * 200  # 200자
    cache.set(long_key, {"v": 1})
    result = cache.get(long_key)
    assert result is not None


def test_cache_corrupted_file(cache, temp_cache_dir):
    """손상된 캐시 파일 처리 테스트"""
    cache_path = temp_cache_dir / "corrupted.json"
    cache_path.write_text("not valid json {{{")

    # 손상된 파일 조회 시 None 반환
    result = cache.get("corrupted")
    assert result is None

    # 손상된 파일 삭제됨
    assert not cache_path.exists()


def test_cache_serialization_error(cache):
    """직렬화 불가능한 데이터 테스트"""
    # set은 default=str로 처리하므로 에러 안 남
    cache.set("func_key", {"func": lambda x: x})  # 함수는 직렬화 불가
    # 하지만 default=str로 처리됨


# =============================================================================
# CacheTTL 상수 테스트
# =============================================================================


def test_cache_ttl_constants():
    """캐시 TTL 상수 테스트"""
    assert CacheTTL.PRICE == 4
    assert CacheTTL.MARKET_CAP == 24
    assert CacheTTL.SUPPLY == 24
    assert CacheTTL.FUNDAMENTAL == 168
