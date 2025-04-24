# app/api/v1/api.py
from fastapi import APIRouter
from .endpoints import auth, users, routes, places

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# ✅ routes 엔드포인트는 여기서 /routes 로 마운트
api_router.include_router(routes.router, prefix="/routes", tags=["routes"])

api_router.include_router(places.router, prefix="/places", tags=["places"])