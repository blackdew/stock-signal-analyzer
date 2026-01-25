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


# =============================================================================
# 태스크별 로그 핸들러
# =============================================================================


class TaskLogHandler(logging.Handler):
    """
    태스크별 로그를 AppState에 전달하는 핸들러.

    특정 태스크 실행 중에만 활성화되며, 로그 메시지를 AppState.task_logs에 저장합니다.
    """

    def __init__(self, task_id: str, app_state: "AppState"):
        """
        Args:
            task_id: 태스크 ID
            app_state: AppState 인스턴스
        """
        super().__init__()
        self.task_id = task_id
        self.app_state = app_state

        # 분석 관련 로거만 캡처
        self.target_loggers = {
            # 기존 에이전트 로거
            "Orchestrator",
            "RankingAgent",
            "StockAnalyzer",
            "SectorAnalyzer",
            "MarketDataAgent",
            "FundamentalAgent",
            "NewsAgent",
            "StockReportAgent",
            "SectorReportAgent",
            "SummaryAgent",
            # 추가 모듈 로거
            "src.data.fetcher",
            "src.core.llm",
            "src.core.rubric",
            "src.data.cache",
        }

        # src. 접두사로 시작하는 모든 로거 허용
        self.src_prefix = "src."

    def emit(self, record: logging.LogRecord) -> None:
        """로그 레코드를 AppState에 전달합니다."""
        # 분석 관련 로거의 메시지만 캡처
        # 1. src. 접두사로 시작하는 모든 로거 허용
        # 2. target_loggers에 명시된 로거 허용
        # 3. target_loggers의 이름으로 시작하는 로거 허용
        if (
            record.name.startswith(self.src_prefix)
            or record.name in self.target_loggers
            or any(record.name.startswith(name) for name in self.target_loggers)
        ):
            try:
                level = record.levelname.lower()
                message = self.format(record)
                self.app_state.add_task_log(self.task_id, message, level)
            except Exception:
                # 로그 핸들러에서 예외가 발생하면 무시
                pass


_active_task_handlers: dict[str, TaskLogHandler] = {}


def register_task_log_handler(task_id: str, app_state: "AppState") -> TaskLogHandler:
    """
    태스크별 로그 핸들러를 등록합니다.

    Args:
        task_id: 태스크 ID
        app_state: AppState 인스턴스

    Returns:
        TaskLogHandler 인스턴스
    """
    handler = TaskLogHandler(task_id, app_state)

    # 간결한 포맷 사용
    formatter = logging.Formatter("%(name)s | %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    # 루트 로거에 핸들러 추가
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    # 활성 핸들러 저장
    _active_task_handlers[task_id] = handler

    return handler


def unregister_task_log_handler(task_id: str) -> None:
    """
    태스크별 로그 핸들러를 제거합니다.

    Args:
        task_id: 태스크 ID
    """
    if task_id in _active_task_handlers:
        handler = _active_task_handlers[task_id]
        root_logger = logging.getLogger()
        root_logger.removeHandler(handler)
        del _active_task_handlers[task_id]
