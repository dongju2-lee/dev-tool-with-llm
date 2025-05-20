import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import pathlib
import sys

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, LOG_LEVEL)
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# 전역 로거 저장소
LOGGERS = {}


def setup_logger(name):
    """
    날짜별로 로그를 저장하고 콘솔에도 출력하는 로거를 설정합니다.
    Streamlit 환경에서 로그 중복을 방지하기 위한 로직이 추가되었습니다.
    """
    # 이미 생성된 로거라면 반환
    global LOGGERS  # noqa: F824
    if name in LOGGERS:
        return LOGGERS[name]

    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # 이미 핸들러가 설정되어 있다면 추가하지 않음
    if logger.handlers:
        LOGGERS[name] = logger
        return logger

    # 로그 디렉토리가 없으면 생성
    pathlib.Path(LOG_DIR).mkdir(exist_ok=True)

    # 파일명에 날짜를 포함시켜 로그 파일을 생성
    log_file = os.path.join(
        LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    # 파일 핸들러 설정 - 날짜별로 파일 교체
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,  # 30일간의 로그 유지
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.setLevel(LOG_LEVEL)

    # 스트림릿 환경에서는 콘솔 출력 최소화
    is_streamlit = "streamlit" in sys.modules
    console_level = logging.WARNING if is_streamlit else LOG_LEVEL

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    console_handler.setLevel(console_level)

    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 로거 캐시
    LOGGERS[name] = logger

    return logger


# 기본 로거 설정
default_logger = setup_logger("smart_home_agent")