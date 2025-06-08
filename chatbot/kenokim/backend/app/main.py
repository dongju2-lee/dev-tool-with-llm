import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("Starting app/main.py import...")

try:
    from .core.config import settings
    print("Settings imported successfully")
except Exception as e:
    print(f"Error importing settings: {e}")
    raise

try:
    from .api.v1.endpoints import router as v1_router
    print("v1_router imported successfully")
except Exception as e:
    print(f"Error importing v1_router: {e}")
    raise

try:
    from .graph.instance import get_app_graph
    print("get_app_graph imported successfully")
except Exception as e:
    print(f"Error importing get_app_graph: {e}")
    raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 및 종료 시 실행되는 이벤트"""
    # 시작 시: LangGraph 초기화
    logger.info("Initializing DevOps AI Assistant...")
    try:
        await get_app_graph()
        logger.info("LangGraph initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LangGraph: {str(e)}")
        
    yield
    
    # 종료 시: 리소스 정리
    logger.info("Shutting down DevOps AI Assistant...")


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성하고 설정합니다."""
    
    print("Creating FastAPI app...")
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="LangGraph 기반 DevOps AI 어시스턴트 API",
        lifespan=lifespan
    )
    
    print("FastAPI app created")
    
    # CORS 미들웨어 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
    )
    
    print("CORS middleware added")
    
    # API 라우터 포함
    app.include_router(
        v1_router,
        prefix="/api/v1",
        tags=["v1"]
    )
    
    print("Router included")
    
    # 루트 엔드포인트
    @app.get("/")
    async def root():
        return {
            "message": "DevOps AI Assistant API에 오신 것을 환영합니다!",
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health"
        }
    
    print("Root endpoint added")
    
    return app


print("About to create app instance...")

# FastAPI 앱 인스턴스 생성
try:
    app = create_app()
    print("App instance created successfully")
except Exception as e:
    print(f"Error creating app instance: {e}")
    import traceback
    traceback.print_exc()
    raise

print("app/main.py import completed successfully")

# If you want to run this directly using `python app/main.py` for simple testing (though uvicorn is better)
# import uvicorn
# if __name__ == "__main__":
# uvicorn.run(app, host="0.0.0.0", port=8000) 