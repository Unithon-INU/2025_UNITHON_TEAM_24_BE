# app/core/security.py

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from jose import jwt
import firebase_admin
from firebase_admin import auth, credentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import schemas, models
from app.crud import crud_user
from app.db.database import get_db

# --- JWT 생성 함수 ---
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    주어진 데이터로 액세스 토큰(JWT)을 생성합니다.
    """
    if not settings.SECRET_KEY:
        raise ValueError("JWT Secret Key is not configured.")

    to_encode = data.copy()
    expire = (
        datetime.now(timezone.utc) + expires_delta
        if expires_delta
        else datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    if "sub" not in to_encode:
        print("Warning: 'sub' claim not found in token data.")

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# --- Firebase Admin SDK 초기화 함수 ---
def initialize_firebase_admin() -> None:
    """
    앱 시작 시 호출하여 Firebase Admin SDK를 초기화합니다.
    """
    if settings.FIREBASE_SDK_INITIALIZED or firebase_admin._apps:
        return

    cred_path = settings.GOOGLE_APPLICATION_CREDENTIALS
    if not cred_path or not os.path.exists(cred_path):
        raise RuntimeError(f"Firebase credentials not found at {cred_path!r}")

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    settings.FIREBASE_SDK_INITIALIZED = True
    print("Firebase Admin SDK initialized.")


# --- Firebase 토큰 검증 및 사용자 조회/생성 의존성 ---
async def get_current_user_from_firebase_token(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Header 'Authorization: Bearer <id_token>' 로 전달된 Firebase ID 토큰을 검증하고,
    DB에 사용자가 없으면 생성한 뒤 models.User 인스턴스를 반환합니다.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    id_token = authorization.split("Bearer ")[1]

    # 1) Firebase 토큰 검증
    try:
        decoded = auth.verify_id_token(id_token)
    except auth.ExpiredIdTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    # 2) UID, 이메일 등 추출
    uid = decoded.get("uid")
    email = decoded.get("email", "")

    # 3) Pydantic 스키마 인스턴스 생성
    user_in = schemas.UserCreate(
        id=uid,                   # Firebase UID (Optional[str] 로 정의되어 있어야 합니다)
        email=email,
        name=decoded.get("name"),
        profile_image_url=decoded.get("picture"),
        hashed_password=None      # 소셜 로그인에는 비밀번호가 없으므로 None
    )

    # 4) DB에서 조회하거나 새로 생성
    user = crud_user.get_or_create_user_firebase(db=db, user_in=user_in)
    if not user:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User creation failed")

    return user