"""
로깅 유틸리티 모듈

주식 신호 분석 앱의 로깅 시스템을 제공합니다.
"""

import logging
import os
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    로거 설정 및 생성

    Args:
        name: 로거 이름 (일반적으로 모듈의 __name__ 사용)
        log_file: 로그 파일 경로 (None이면 파일 로깅 안 함)
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        설정된 Logger 인스턴스

    Example:
        >>> logger = setup_logger(__name__, 'logs/app.log', logging.DEBUG)
        >>> logger.info("애플리케이션 시작")
    """
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 핸들러가 이미 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()

    # 포매터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 (선택적)
    if log_file:
        # 디렉토리 생성
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 부모 로거의 핸들러 사용 방지 (중복 로그 방지)
    logger.propagate = False

    return logger


def get_default_log_file(prefix: str = 'analysis') -> str:
    """
    기본 로그 파일 경로 생성

    Args:
        prefix: 로그 파일명 접두사

    Returns:
        로그 파일 경로 (예: 'logs/analysis_20251022.log')
    """
    today = datetime.now().strftime('%Y%m%d')
    log_file = f'logs/{prefix}_{today}.log'
    return log_file


# 전역 로거 (선택적 사용)
_global_logger: Optional[logging.Logger] = None


def get_logger(name: str = __name__, use_file: bool = True) -> logging.Logger:
    """
    로거 가져오기 (편의 함수)

    Args:
        name: 로거 이름
        use_file: 파일 로깅 사용 여부

    Returns:
        Logger 인스턴스
    """
    log_file = get_default_log_file() if use_file else None
    return setup_logger(name, log_file)
