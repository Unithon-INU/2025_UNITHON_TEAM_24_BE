# ./app/main.py

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# --- 설정, 라우터, 초기화 함수 등 import ---
from app.api.v1.api import api_router
from app.core.config import settings
from app.db.database import init_db # 선택 사항 (Alembic 사용 안 할 시)
from app.core.security import initialize_firebase_admin

# --- 👇 FastAPI 앱 인스턴스 생성 (가장 먼저!) ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json", # API 문서 경로
    version="0.1.0",
    description="PathMaker AI Flutter 앱을 위한 백엔드 API"
)

# --- 👇 미들웨어 설정 (app 객체 생성 후) ---
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5905",
    "http://127.0.0.1:5905",
    "http://127.0.0.1",
    # Flutter 웹 앱 실제 배포 주소 추가
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 시 "*" 사용, 운영 시 origins 리스트 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Added to expose all headers, which helps with image responses
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    print("Application startup...")
    initialize_firebase_admin()
    print("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행될 작업"""
    print("Application shutdown...")
    print("Application shutdown complete.")

# --- 👇 기본 루트 엔드포인트 정의 (app 객체 생성 후) ---
@app.get("/", tags=["Root"])
async def read_root():
    """API 루트. 서비스 상태 확인용."""
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"}
# --- 👆 ---

# --- 👇 전역 예외 처리기 (app 객체 생성 후) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error", "errors": exc.errors()},
    )
# ... (다른 예외 처리기) ...
# --- 👆 ---

# --- 서버 실행 (개발 시 터미널에서 uvicorn 사용) ---
# 이 파일 자체를 직접 실행하는 것이 아니라 uvicorn 명령어를 사용합니다.
# 예: uvicorn app.main:app --reload --host 0.0.0.0 --port 5904