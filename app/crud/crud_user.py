# app/crud/crud_user.py

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.db import models, schemas
from app.core.hash_utils import hash_password, verify_password


def get_user(db: Session, user_id: str) -> Optional[models.User]:
    """
    ID(자체 UUID 또는 Firebase UID)로 사용자 조회
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """
    이메일로 사용자 조회
    """
    return db.query(models.User).filter(models.User.email == email).first()


def create_db_user(db: Session, user: schemas.UserCreateSignup) -> models.User:
    """
    이메일/비밀번호 기반 신규 사용자 생성
    - schemas.UserCreateSignup 에는 email, name, password 필드가 있습니다.
    - models.User 에는 password_hash 컬럼이 있어야 합니다.
    """
    hashed = hash_password(user.password)
    db_user = models.User(
        id=str(uuid.uuid4()),      # 자체 UUID 생성
        email=user.email,
        name=user.name,
        password_hash=hashed,      # models.User 에 정의된 컬럼 이름과 일치시킬 것
        is_active=True
    )
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except Exception:
        db.rollback()
        raise
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    """
    이메일/비밀번호로 로그인 시 사용자 인증
    """
    user = get_user_by_email(db, email=email)
    if not user or not getattr(user, "password_hash", None):
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def get_or_create_user_firebase(db: Session, user_in: schemas.UserCreate) -> models.User:
    """
    Firebase 토큰 검증 후 호출.
    - user_in.id 에는 Firebase UID
    - user_in.email, .name, .profile_image_url 등이 담겨 있음
    """
    # 1) UID가 있으면 UID로, 없으면 이메일로 조회
    if user_in.id:
        db_user = get_user(db, user_id=user_in.id)
    else:
        db_user = get_user_by_email(db, email=user_in.email)  # 이메일 로그인 전용 분기

    if db_user:
        # 이미 존재하면 바로 반환
        return db_user

    # 2) 새 소셜 사용자 생성
    db_user = models.User(
        id=user_in.id or str(uuid.uuid4()),
        email=user_in.email,
        name=user_in.name,
        profile_image_url=user_in.profile_image_url,
        is_active=True,
        # password_hash 는 소셜에는 None
    )
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except Exception:
        db.rollback()
        raise
    return db_user


def update_user(
    db: Session,
    user_id: str,
    user_in: schemas.UserUpdate
) -> Optional[models.User]:
    """
    사용자 정보 수정:
    - name, password, is_active 항목만 업데이트
    """
    db_user = get_user(db, user_id=user_id)
    if not db_user:
        return None

    if user_in.name is not None:
        db_user.name = user_in.name
    if user_in.password is not None:
        db_user.password_hash = hash_password(user_in.password)
    if user_in.is_active is not None:
        db_user.is_active = user_in.is_active

    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except Exception:
        db.rollback()
        raise
    return db_user


def delete_user(db: Session, user_id: str) -> Optional[models.User]:
    """
    사용자 삭제
    """
    db_user = get_user(db, user_id=user_id)
    if not db_user:
        return None

    db.delete(db_user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return db_user