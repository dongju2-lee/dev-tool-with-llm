import streamlit as st
import requests
from utils.logger_config import setup_logger
from config import *  # Import all constants and configuration values

# 로거 설정'
logger = setup_logger("rag_page", level=LOG_LEVEL)

def rag_page():
    """
    모바일 앱 연동 페이지입니다.
    """
    st.title("📱 모바일 앱 연동")
    st.markdown("---")
    
    # 페이지 설명
    st.markdown("""
    스마트홈 시스템의 모바일 앱과 연동된 정보를 확인하고 관리할 수 있는 페이지입니다.
    사용자 메시지, 개인화 정보, 캘린더 등의 정보를 확인하고 업데이트할 수 있습니다.
    """)
    
    