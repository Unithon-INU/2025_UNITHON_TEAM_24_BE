from typing import Optional, List, Any
from pydantic import BaseModel, HttpUrl, ConfigDict

class PlaceBase(BaseModel):
    google_place_id: str
    name: str
    address: Optional[str] = None
    latitude: float
    longitude: float
    types: Optional[List[str]] = None
    rating: Optional[float] = None
    photo_references: Optional[List[str]] = None
    user_ratings_total: Optional[int] = None  # Add this field for total review count from Google

    # Add these fields:
    type: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class PlaceCreate(PlaceBase):
    """생성용 스키마 (PlaceBase 그대로)"""
    pass

class PlaceUpdate(BaseModel):
    """업데이트용 스키마 (모두 Optional)"""
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    types: Optional[List[str]] = None
    photo_references: Optional[List[str]] = None
    website: Optional[HttpUrl] = None
    phone_number: Optional[str] = None
    operating_hours: Optional[List[str]] = None
    image_url: Optional[HttpUrl] = None
    tags: Optional[List[str]] = None
    reviews: Optional[List[Any]] = None

class Place(PlaceBase):
    description: Optional[str] = None
    type: Optional[str] = None
    operating_hours: Optional[List[str]] = None
    image_url: Optional[HttpUrl] = None
    tags: Optional[List[str]] = None
    reviews: Optional[List[dict]] = None
    reviews_count: Optional[int] = None  # This will be the actual count of reviews we fetch

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=lambda s: s,  # snake_case 그대로 사용
    )