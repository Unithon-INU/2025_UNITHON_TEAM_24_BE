# unithon_backend/app/db/schemas/review.py
from pydantic import BaseModel, Field, ConfigDict # ConfigDict 추가
from typing import Optional
from datetime import datetime
# 응답에 포함될 수 있는 관련 스키마 (필요시 주석 해제)
# from .user import User
# from .place import Place

class ReviewBase(BaseModel):
    rating: float = Field(..., ge=0, le=5, description="0점에서 5점 사이의 평점")
    text: Optional[str] = None  # Changed from 'comment' to 'text' to match database model
    author_name: Optional[str] = None
    profile_photo_url: Optional[str] = None
    relative_time_description: Optional[str] = None

    # --- Pydantic V2 스타일 설정 추가 ---
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    # --- 설정 끝 ---

class ReviewCreate(ReviewBase):
    # 생성 시 place_id는 경로 파라미터로 받고, owner_id는 현재 사용자 정보로 설정하므로
    # 요청 본문에는 rating과 text만 필요할 수 있음.
    pass

class ReviewUpdate(BaseModel): # 업데이트는 필요한 필드만 받도록 BaseModel 상속
    rating: Optional[float] = Field(None, ge=0, le=5)
    text: Optional[str] = None  # Changed from 'comment' to 'text'

    # 업데이트 스키마에도 설정 적용 (필요한 경우)
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

class ReviewInDBBase(ReviewBase):
    id: int  # Changed to int to match database model
    owner_id: Optional[str] = None  # Changed from int to str and made optional
    place_google_id: str  # Changed to match the database model field name
    created_at: datetime

    # model_config는 Base에서 상속받음

class Review(ReviewInDBBase):
    # API 응답 시 포함될 수 있는 추가 정보 (예: 작성자 정보)
    # owner: Optional[User] = None # 예시: 작성자 정보 포함
    # place: Optional[Place] = None # 예시: 장소 정보 포함

    # model_config는 Base에서 상속받음
    pass