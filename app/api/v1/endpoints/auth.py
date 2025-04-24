from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.api import deps # 수정된 deps 사용
from app.db import models, schemas
from app.crud import crud_user
from app.core import security
from app.core.config import settings

router = APIRouter()

@router.post(
    "/signup",
    response_model=schemas.Token, # 가입 성공 시 토큰 반환
    status_code=status.HTTP_201_CREATED,
    summary="Create new user with email and password",
    description="Registers a new user with email, password, and name. Requires 'password_hash' column in User model. Returns an access token."
)
async def signup_new_user(
    *, # 키워드 인자로만 받도록 강제
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreateSignup = Body(...)
):
    """
    새로운 사용자를 이메일, 비밀번호, 이름으로 회원가입시킵니다.
    DB에 password_hash 컬럼이 필요합니다.
    """
    user = crud_user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists.",
        )
    try:
        # CRUD 함수에서 비밀번호 해싱 및 DB 저장 (password_hash 컬럼 필요)
        new_user = crud_user.create_db_user(db=db, user=user_in)
    except AttributeError:
         # 모델에 password_hash 컬럼이 없는 경우 등
         print("Error: 'password_hash' attribute likely missing from User model or DB schema.")
         raise HTTPException(status_code=500, detail="Server configuration error during signup.")
    except Exception as e:
         print(f"Error during signup DB operation: {e}")
         raise HTTPException(
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
             detail="Registration failed."
         )

    # 회원가입 성공 후 토큰 생성
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": new_user.id}, expires_delta=access_token_expires
    )
    return schemas.Token(access_token=access_token, token_type="bearer")


@router.post(
    "/token",
    response_model=schemas.Token,
    summary="Login for access token (email/password)",
    description="Authenticates with email/password (form data), returns JWT."
)
async def login_for_access_token_email_password(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends() # username=email
):
    """
    이메일/비밀번호로 사용자를 인증하고 액세스 토큰(JWT)을 발급합니다.
    DB에 password_hash 컬럼 및 관련 로직이 필요합니다.
    """
    user = crud_user.authenticate_user( # 비밀번호 검증 함수 호출
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}, # Bearer 토큰 방식임을 알림
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # JWT 생성 시 사용자 ID (자체 UUID 또는 Firebase UID)를 'sub'으로 사용
    access_token = security.create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    return schemas.Token(access_token=access_token, token_type="bearer")


@router.post(
    "/login",
    response_model=schemas.Token,
    summary="Confirm login after social auth (using Firebase token)",
    description="Verifies Firebase ID token from header, returns backend JWT."
)
async def login_confirm_social(
    # 헤더의 Firebase ID 토큰 검증 및 사용자 조회/생성은 의존성이 처리
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    (Flutter Google 로그인 후 호출됨)
    헤더의 Firebase ID 토큰으로 인증된 사용자에 대해 백엔드 JWT를 발급합니다.
    """
    user_id = current_user.id # 인증된 사용자의 ID (Firebase UID)

    # 해당 사용자 ID로 백엔드 JWT 생성
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user_id}, expires_delta=access_token_expires
    )
    # Flutter 앱이 기대하는 'token' 필드를 포함한 응답 반환
    return schemas.Token(access_token=access_token, token_type="bearer")