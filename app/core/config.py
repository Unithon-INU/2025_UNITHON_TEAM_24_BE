import os
from pydantic_settings import BaseSettings # pydantic -> pydantic_settings 로 변경
from dotenv import load_dotenv
from pathlib import Path

# 프로젝트 루트의 .env 파일을 로드하도록 경로 설정
# 이 파일은 프로젝트 루트에 있다고 가정
env_path = Path('.') / '.env'
# load_dotenv 호출을 main.py나 앱 시작 지점으로 옮기는 것을 고려해볼 수 있음
if env_path.is_file():
    load_dotenv(dotenv_path=env_path)
    print(f".env file loaded from: {env_path.resolve()}")
else:
    print(f"Warning: .env file not found at {env_path.resolve()}")


class Settings(BaseSettings):
    PROJECT_NAME: str = "PathMaker AI Backend"
    API_V1_STR: str = "/api/v1"

    # 환경 변수에서 읽거나 기본값 사용
    DATABASE_URL: str
    GOOGLE_PLACES_API_KEY: str | None = None
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Firebase Admin SDK 초기화 상태 플래그 (런타임에서 관리)
    FIREBASE_SDK_INITIALIZED: bool = False

    class Config:
        # .env 파일 우선순위 및 인코딩 설정 (pydantic-settings 방식)
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = True # 환경 변수 이름 대소문자 구분
        extra = 'ignore' # <-- 이 줄을 추가하여 정의되지 않은 환경 변수 무시


# 설정 객체 생성 (환경 변수 및 .env 파일에서 값을 읽어옴)
try:
    settings = Settings()
    # 필수 환경 변수 누락 시 여기서 에러 발생 가능
    print(f"Settings loaded. DB URL: {settings.DATABASE_URL}")
    print(f"Google Places API Key loaded: {'Yes' if settings.GOOGLE_PLACES_API_KEY else 'No'}")
    print(f"Firebase Credentials Path loaded: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
    print(f"JWT Secret Key loaded: {'Yes' if hasattr(settings, 'SECRET_KEY') and settings.SECRET_KEY != 'your_very_secret_key_here_please_change_this' else 'No or Default!'}")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to load settings. Check .env file and environment variables. Error: {e}")
    # 실제 운영 환경에서는 앱 실행을 중단해야 할 수 있음
    # 임시 기본값으로라도 실행되게 하려면 Settings 클래스 필드에 기본값 설정
    settings = None # 설정 로드 실패 시 None으로 설정 (이후 코드에서 None 체크 필요)