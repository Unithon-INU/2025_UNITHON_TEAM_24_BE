# app/db/schemas/route.py

from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel

from .place import Place  # 응답 시 full Place 객체를 포함
from .place import PlaceBase  # 필요하다면 import


class PlaceRef(BaseModel):
    google_place_id: str

    class Config:
        from_attributes = True


class TravelRouteBase(BaseModel):
    name: str
    description: Optional[str] = None
    places: List[PlaceRef]
    moving_info: Optional[List[Any]] = []
    estimated_duration: Optional[str] = None
    total_distance: Optional[str] = None


class TravelRouteCreate(TravelRouteBase):
    pass


class TravelRouteUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    places: Optional[List[PlaceRef]] = None
    moving_info: Optional[List[Any]] = None
    estimated_duration: Optional[str] = None
    total_distance: Optional[str] = None


class TravelRouteInDBBase(TravelRouteBase):
    id: str
    owner_id: str
    created_at: datetime

    class Config:
        
        from_attributes = True


class TravelRoute(TravelRouteInDBBase):
    places: List[Place]  # 응답할 때는 전체 Place 스키마