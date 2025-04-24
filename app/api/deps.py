from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.core.security import get_current_user_from_firebase_token # 이름 변경된 함수 사용
# from app.core.security import get_current_user_from_backend_token # 자체 JWT 사용 시
from app.db import models

# DB 세션 의존성
def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 의존성 주입"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 현재 활성 사용자 의존성 (Firebase 토큰 기반)
async def get_current_active_user(
    current_user: models.User = Depends(get_current_user_from_firebase_token)
) -> models.User:
    """Firebase 토큰으로 인증된 사용자를 반환합니다. 필요시 추가 검증 가능."""
    # 예: 사용자 비활성화 상태 체크
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# (참고) 백엔드 JWT 기반 사용자 의존성 (필요시)
# async def get_current_active_user_jwt(
#     current_user: models.User = Depends(get_current_user_from_backend_token)
# ) -> models.User:
#     # ... 추가 검증 ...
#     return current_user