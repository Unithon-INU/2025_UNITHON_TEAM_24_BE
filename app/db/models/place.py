import datetime
import uuid
from sqlalchemy import Column, String, Float, Text, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from sqlalchemy.sql import func, expression
from typing import List
from sqlalchemy.dialects.postgresql import ARRAY

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Place(Base):
    __tablename__ = "places"

    google_place_id    = Column(String, primary_key=True, index=True, default=generate_uuid)
    name               = Column(String, nullable=False)
    address            = Column(String, nullable=True)
    latitude           = Column(Float, nullable=False)
    longitude          = Column(Float, nullable=False)
    rating             = Column(Float, nullable=True)
    user_ratings_total = Column(Integer, nullable=True)
    types              = Column(JSON, nullable=True)  # Changed from ARRAY(String) to JSON
    photo_references   = Column(JSON, nullable=True)  # Changed from ARRAY(String) to JSON
    website            = Column(String, nullable=True)
    phone_number       = Column(String, nullable=True)
    description        = Column(Text, nullable=True)
    operating_hours    = Column(JSON, nullable=True)  # Changed from ARRAY(String) to JSON
    image_url          = Column(String, nullable=True)
    tags               = Column(JSON, nullable=True)  # Changed from ARRAY(String) to JSON
    created_at         = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 기존: 리뷰와의 양방향 매핑
    reviews = relationship(
        "Review",
        back_populates="place",
        cascade="all, delete-orphan",
    )

    # ── 수정된 부분: RoutePlace와의 양방향 매핑
    route_associations = relationship(
        "RoutePlace",
        back_populates="place",
        cascade="all, delete-orphan",
    )