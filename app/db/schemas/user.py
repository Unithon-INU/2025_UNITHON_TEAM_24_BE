# app/db/schemas/user.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, HttpUrl


class UserBase(BaseModel):
    """공통 필드"""
    email: EmailStr = Field(..., description="사용자 이메일 (로그인 ID)")
    name: Optional[str] = Field(None, description="사용자 이름")
    profile_image_url: Optional[HttpUrl] = Field(
        None, description="프로필 이미지 URL"
    )
    is_active: bool = Field(True, description="사용자 활성 여부")

    model_config = ConfigDict(from_attributes=True)


class UserCreateSignup(UserBase):
    """회원가입 시 클라이언트에서 받을 필드"""
    password: str = Field(..., min_length=6, description="비밀번호 (평문)")


class UserCreate(UserBase):
    id: Optional[str] = Field(
        None,
        description="(옵션) 사용자 고유 ID (Firebase UID)"
    )
    hashed_password: Optional[str] = Field(
        None,
        description="(옵션) 해시된 비밀번호"
    )


class UserUpdate(BaseModel):
    """사용자 정보 수정 시 사용"""
    name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class UserInDBBase(UserBase):
    """DB에 저장된 공통 필드 (읽기 전용)"""
    id: str = Field(..., description="사용자 고유 ID (UUID 또는 Firebase UID)")
    created_at: datetime = Field(..., description="생성 일시")
    updated_at: Optional[datetime] = Field(None, description="수정 일시")

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    """API 응답용 사용자 스키마"""
    pass


class UserInDB(UserInDBBase):
    """DB 내부용 (해시비밀번호 포함)"""
    hashed_password: str