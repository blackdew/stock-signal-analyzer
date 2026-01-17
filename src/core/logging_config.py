"""
Logging Configuration

애플리케이션 로깅 설정.
콘솔과 파일에 동시 출력, RotatingFileHandler 사용.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


# 로그 디렉토리
DEFAULT_LOG_DIR = Path("output/logs")


def setup_logging(
    verbose: bool = False,
    log_dir: Path = DEFAULT_LOG_DIR,
    log_file: str = "analysis.log",
) -> None:
    """
    애플리케이션 로깅을 설정합니다.

    Args:
        verbose: True면 DEBUG 레벨, False면 INFO 레벨
        log_dir: 로그 파일 디렉토리
        log_file: 로그 파일명
    """
    # 로그 디렉토리 생성
    log_dir.mkdir(parents=True, exist_ok=True)

    # 로그 레벨 설정
    level = logging.DEBUG if verbose else logging.INFO

    # 포맷터
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # 파일 핸들러 (10MB, 5개 백업)
    log_path = log_dir / log_file
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # 파일에는 항상 DEBUG 레벨
    file_handler.setFormatter(formatter)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 기존 핸들러 제거 (중복 방지)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 새 핸들러 추가
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 설정 완료 로그
    logging.info(f"로깅 설정 완료 (레벨: {'DEBUG' if verbose else 'INFO'})")
    logging.debug(f"로그 파일: {log_path}")


def get_logger(name: str) -> logging.Logger:
    """
    명명된 로거를 반환합니다.

    Args:
        name: 로거 이름

    Returns:
        logging.Logger
    """
    return logging.getLogger(name)
