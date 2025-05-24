"""
로거 구성 모듈

애플리케이션 전체에서 일관된 로깅 형식을 제공하는 로거 설정입니다.
"""

import os
import sys
import logging
from logging import Logger
from typing import Optional, Union, Dict, Any
from datetime import datetime

def setup_logger(
    name: str, 
    level: int = logging.INFO,
    log_format: Optional[str] = None,
    log_file: Optional[str] = None
) -> Logger:
    """
    로거 인스턴스를 설정하고 반환합니다.
    
    Args:
        name: 로거 이름
        level: 로깅 레벨 (기본값: INFO)
        log_format: 로그 형식 (기본값: None)
        log_file: 로그 파일 경로 (기본값: None)
        
    Returns:
        구성된 로거 인스턴스
    """
    # 기본 로그 형식
    if log_format is None:
        log_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(filename)s:%(lineno)d | %(message)s"
        )
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 로거의 모든 핸들러가 이미 구성되었는지 확인
    if not logger.handlers:
        # 콘솔 핸들러 추가
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # 파일 핸들러 추가 (필요한 경우)
        if log_file:
            # 로그 디렉토리가 없는 경우 생성
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(log_format)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
    
    return logger


def log_execution_time(logger: Logger):
    """
    함수의 실행 시간을 로깅하는 데코레이터
    
    Args:
        logger: 로그 메시지를 기록할 로거 인스턴스
        
    Returns:
        실행 시간을 로깅하는 데코레이터 함수
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            logger.debug(f"{func.__name__} 실행 시작")
            
            result = func(*args, **kwargs)
            
            end_time = datetime.now()
            execution_time = end_time - start_time
            logger.debug(f"{func.__name__} 실행 완료. 소요 시간: {execution_time}")
            
            return result
        return wrapper
    return decorator


def log_async_execution_time(logger: Logger):
    """
    비동기 함수의 실행 시간을 로깅하는 데코레이터
    
    Args:
        logger: 로그 메시지를 기록할 로거 인스턴스
        
    Returns:
        비동기 함수의 실행 시간을 로깅하는 데코레이터 함수
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            logger.debug(f"{func.__name__} 비동기 실행 시작")
            
            result = await func(*args, **kwargs)
            
            end_time = datetime.now()
            execution_time = end_time - start_time
            logger.debug(f"{func.__name__} 비동기 실행 완료. 소요 시간: {execution_time}")
            
            return result
        return wrapper
    return decorator 