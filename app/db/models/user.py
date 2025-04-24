#app/db/models/user.py

import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.db.base_class import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id             = Column(String, primary_key=True, default=generate_uuid, index=True)
    email          = Column(String, unique=True, index=True, nullable=False)
    name           = Column(String, nullable=True)
    is_active      = Column(Boolean, default=True)
    is_superuser   = Column(Boolean, default=False)
    created_at     = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # — 수정된 부분: Review 모델과 양방향 관계 설정
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")

    # (필요에 따라 Route 등 다른 관계도 여기 추가)