from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps
from app.db import models, schemas
# from app.crud import crud_user

router = APIRouter()

@router.get(
    "/profile",
    response_model=schemas.User,
    summary="Get current user profile",
    description="Retrieves the profile of the authenticated user (requires valid token in header)."
)
async def read_current_user_profile(
    # 여기서 사용하는 의존성에 따라 인증 방식 결정됨
    # Firebase 토큰 기반: current_user: models.User = Depends(deps.get_current_active_user)
    # 백엔드 JWT 기반: current_user: models.User = Depends(deps.get_current_active_user_jwt) # 예시 이름
    # 현재는 Firebase 토큰 기반 사용
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    인증된 사용자의 프로필 정보를 반환합니다.
    요청 헤더에 유효한 토큰(현재는 Firebase ID 토큰)이 필요합니다.
    """
    return current_user

# TODO: 프로필 업데이트 엔드포인트 (PUT /profile)
# TODO: 계정 삭제 엔드포인트 (DELETE /profile)