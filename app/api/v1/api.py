# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import places, routes, users, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(routes.router, prefix="/routes", tags=["routes"])
api_router.include_router(places.router, prefix="/places", tags=["places"])

# 공개 API 경로를 별도로 추가
from app.api.v1.endpoints.routes import read_public_route
public_router = APIRouter()
public_router.add_api_route(
    "/routes/{route_id}", 
    read_public_route, 
    methods=["GET"], 
    tags=["public"]
)
api_router.include_router(public_router, prefix="/public", tags=["public"])