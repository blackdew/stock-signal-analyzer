"""
헬퍼 유틸리티 모듈

안전한 계산을 위한 유틸리티 함수들을 제공합니다.
"""

import pandas as pd
import numpy as np
from typing import Union


def safe_divide(
    numerator: Union[float, int],
    denominator: Union[float, int],
    default: float = 0.0
) -> float:
    """
    안전한 나눗셈 (Division by zero 방지)

    Args:
        numerator: 분자
        denominator: 분모
        default: 나눗셈 불가능 시 반환할 기본값

    Returns:
        나눗셈 결과 또는 기본값

    Example:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0)
        0.0
        >>> safe_divide(10, 0, default=-1.0)
        -1.0
    """
    # 분모가 0이거나 NaN인 경우
    if denominator == 0 or pd.isna(denominator):
        return default

    # 분자가 NaN인 경우
    if pd.isna(numerator):
        return default

    # 계산 수행
    result = numerator / denominator

    # 결과가 NaN 또는 Inf인 경우
    if pd.isna(result) or np.isinf(result):
        return default

    return float(result)


def safe_percentage(
    value: Union[float, int],
    base: Union[float, int],
    default: float = 0.0
) -> float:
    """
    안전한 백분율 계산

    Args:
        value: 값
        base: 기준값
        default: 계산 불가능 시 반환할 기본값

    Returns:
        백분율 (예: 0.1 for 10%)

    Example:
        >>> safe_percentage(50, 100)
        0.5
        >>> safe_percentage(50, 0)
        0.0
    """
    if base == 0 or pd.isna(base) or pd.isna(value):
        return default

    result = (value - base) / base

    if pd.isna(result) or np.isinf(result):
        return default

    return float(result)


def safe_float(value: any, default: float = 0.0) -> float:
    """
    안전한 float 변환

    Args:
        value: 변환할 값
        default: 변환 불가능 시 반환할 기본값

    Returns:
        float 값 또는 기본값

    Example:
        >>> safe_float("123.45")
        123.45
        >>> safe_float("invalid")
        0.0
        >>> safe_float(None, -1.0)
        -1.0
    """
    try:
        if value is None or pd.isna(value):
            return default

        result = float(value)

        if pd.isna(result) or np.isinf(result):
            return default

        return result

    except (ValueError, TypeError):
        return default


def is_valid_number(value: any) -> bool:
    """
    유효한 숫자인지 검증

    Args:
        value: 검증할 값

    Returns:
        True if valid number, False otherwise

    Example:
        >>> is_valid_number(123.45)
        True
        >>> is_valid_number(np.nan)
        False
        >>> is_valid_number(np.inf)
        False
    """
    if value is None:
        return False

    if pd.isna(value):
        return False

    if np.isinf(value):
        return False

    return True


def clip_value(
    value: Union[float, int],
    min_value: Union[float, int] = None,
    max_value: Union[float, int] = None
) -> float:
    """
    값을 범위 내로 제한

    Args:
        value: 제한할 값
        min_value: 최소값 (None이면 제한 없음)
        max_value: 최대값 (None이면 제한 없음)

    Returns:
        범위 내로 제한된 값

    Example:
        >>> clip_value(150, 0, 100)
        100
        >>> clip_value(-10, 0, 100)
        0
        >>> clip_value(50, 0, 100)
        50
    """
    if pd.isna(value):
        if min_value is not None:
            return float(min_value)
        elif max_value is not None:
            return float(max_value)
        else:
            return 0.0

    result = float(value)

    if min_value is not None and result < min_value:
        result = float(min_value)

    if max_value is not None and result > max_value:
        result = float(max_value)

    return result
