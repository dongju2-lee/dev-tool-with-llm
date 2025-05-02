"""
Grafana 클라이언트 컨텍스트 관리
"""
import os
from typing import Optional, Dict, Any
import logging
from urllib.parse import urlparse
from .client import GrafanaClient

logger = logging.getLogger("grafana-context")

# 환경 변수 키
GRAFANA_URL_ENV = "GRAFANA_URL"
GRAFANA_API_KEY_ENV = "GRAFANA_API_KEY"

# 기본 Grafana URL
DEFAULT_GRAFANA_URL = "http://localhost:3000"

def get_grafana_info_from_env() -> tuple[str, str]:
    """환경 변수에서 Grafana 정보 추출"""
    url = os.environ.get(GRAFANA_URL_ENV, DEFAULT_GRAFANA_URL).rstrip('/')
    api_key = os.environ.get(GRAFANA_API_KEY_ENV, "")
    
    return url, api_key

class GrafanaContext:
    """Grafana 클라이언트 컨텍스트 관리"""
    
    _instance: Optional['GrafanaContext'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GrafanaContext, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._grafana_url = None
        self._grafana_api_key = None
        self._debug_mode = False
        self._client = None
        self._initialized = True
    
    def initialize(self, url: Optional[str] = None, api_key: Optional[str] = None, debug: bool = False):
        """컨텍스트 초기화"""
        # 환경 변수나 기본값으로부터 URL과 API 키 설정
        env_url, env_api_key = get_grafana_info_from_env()
        
        self._grafana_url = url or env_url
        self._grafana_api_key = api_key or env_api_key
        self._debug_mode = debug
        
        # URL 유효성 검사
        if not self._grafana_url:
            self._grafana_url = DEFAULT_GRAFANA_URL
        
        try:
            parsed_url = urlparse(self._grafana_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid Grafana URL: {self._grafana_url}")
        except Exception as e:
            logger.error(f"Error parsing Grafana URL: {e}")
            self._grafana_url = DEFAULT_GRAFANA_URL
        
        logger.info(f"Grafana URL: {self._grafana_url}, API key set: {bool(self._grafana_api_key)}")
        
        # 클라이언트 생성
        if self._grafana_api_key:
            self._client = GrafanaClient(
                base_url=self._grafana_url,
                api_key=self._grafana_api_key,
                debug=self._debug_mode
            )
    
    @property
    def client(self) -> Optional[GrafanaClient]:
        """Grafana 클라이언트 반환"""
        if self._client is None:
            self.initialize()
        return self._client
    
    @property
    def is_initialized(self) -> bool:
        """컨텍스트가 초기화되었는지 확인"""
        return self._client is not None
    
    def set_debug_mode(self, debug: bool):
        """디버그 모드 설정"""
        self._debug_mode = debug
        if self._client:
            self._client.debug = debug

# 싱글톤 인스턴스
grafana_context = GrafanaContext() 