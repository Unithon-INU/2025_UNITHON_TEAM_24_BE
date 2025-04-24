#app/db/models/review.py

import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Review(Base):
    __tablename__ = "reviews"

    id                      = Column(Integer, primary_key=True, autoincrement=True)  # Changed to Integer to match DB
    owner_id                = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    place_google_id         = Column(String, ForeignKey("places.google_place_id"), nullable=False, index=True)
    rating                  = Column(Integer, nullable=False)
    text                    = Column(Text, nullable=True)
    author_name             = Column(String, nullable=True)
    profile_photo_url       = Column(String, nullable=True)
    relative_time_description = Column(String, nullable=True)
    created_at              = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # — 수정된 부분: User 모델과 양방향 관계 설정
    user = relationship("User", back_populates="reviews")
    # — 기존: Place 모델과 양방향 관계(기존 코드 유지)
    place = relationship("Place", back_populates="reviews")