"""
페이지 상수 및 공통 유틸리티 함수
"""

import streamlit as st
import requests
from PIL import Image
import io
import os
import datetime
from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values

# 로거 설정
logger = setup_logger("helpers", level=LOG_LEVEL)

# 페이지 상수
RAG_PAGE = "RAG"
CHATBOT_PAGE = "챗봇"



def format_timestamp(timestamp):
    """타임스탬프를 읽기 쉬운 형식으로 변환"""
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.error(f"타임스탬프 변환 오류: {str(e)}")
        return "알 수 없는 시간"


def display_agent_graph(graph_type="full"):
    """에이전트 그래프 표시"""
    try:
        st.subheader("에이전트 그래프")
        
        graph_path = f"graphs/{graph_type}_graph.png"
        
        if os.path.exists(graph_path):
            image = Image.open(graph_path)
            st.image(image, use_column_width=True)
        else:
            st.warning(f"그래프 이미지를 찾을 수 없습니다: {graph_path}")
    except Exception as e:
        logger.error(f"에이전트 그래프 표시 오류: {str(e)}")
        st.error(f"에이전트 그래프를 표시할 수 없습니다: {str(e)}")
