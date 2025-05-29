"""
페이지 상수 및 공통 유틸리티 함수
"""

import os
import requests
import datetime

from PIL import Image
import streamlit as st

from utils.logging_config import setup_logger

# 로거 설정
logger = setup_logger("helpers")

# 페이지 상수
CHATBOT_PAGE = "챗봇"
RAG_PAGE = "RAG 문서 관리"
VOICE_CHATBOT_PAGE = "음성 챗봇"
DYNAMIC_UI_PAGE = "다이나믹 UI"

# 모바일 서브페이지 상수
MESSAGES_SUBPAGE = "메시지"
PERSONALIZATION_SUBPAGE = "개인화 설정"
CALENDAR_SUBPAGE = "캘린더"

# 서버 URL
MOCK_SERVER_URL = os.environ.get("MOCK_SERVER_URL", "http://localhost:8503")


def format_timestamp(timestamp):
    """타임스탬프를 읽기 쉬운 형식으로 변환"""
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.error(f"타임스탬프 변환 오류: {str(e)}")
        return "알 수 없는 시간"
