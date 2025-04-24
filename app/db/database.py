from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings # 수정된 config import
from typing import Generator
from sqlalchemy.orm import Session
# SQLAlchemy 엔진 생성
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    # connect_args는 SQLite 사용 시에만 필요할 수 있음
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

# 데이터베이스 세션 로컬 생성기
# autoflush=False: 세션 내 객체 변경 시 즉시 DB 반영 안 함 (commit 시 반영)
# autocommit=False: 자동 커밋 안 함 (명시적 commit 필요)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# DB 테이블 생성 함수 (개발 초기 또는 테스트용)
def init_db():
    """데이터베이스 테이블 생성 (Alembic 사용 시 대체)"""
    # 중요: 모든 모델 클래스가 이 함수 호출 전에 import 되어 Base.metadata에 등록되어야 함
    from app.db.base_class import Base
    from app.db.models.user import User # 모든 모델 import
    from app.db.models.route import DbTravelRoute
    print("Attempting to create database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables check/creation complete.")
    except Exception as e:
        print(f"Error during table creation: {e}")

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()