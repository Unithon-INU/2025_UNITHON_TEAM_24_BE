import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from sqlalchemy.sql import func, expression
from sqlalchemy.dialects.postgresql import ARRAY

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Route(Base):
    __tablename__ = "routes"

    id                 = Column(String, primary_key=True, default=generate_uuid)
    owner_id           = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name               = Column(String, nullable=False)
    description        = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    moving_info        = Column(JSON, nullable=False)
    estimated_duration = Column(String, nullable=True)
    total_distance     = Column(String, nullable=True)

    # RoutePlace와의 양방향 매핑
    places = relationship(
        "RoutePlace",
        back_populates="route",
        cascade="all, delete-orphan",
    )

class RoutePlace(Base):
    __tablename__ = "route_places"

    id               = Column(String, primary_key=True, default=generate_uuid)
    route_id         = Column(String, ForeignKey("routes.id"), nullable=False, index=True)
    place_google_id  = Column(String, ForeignKey("places.google_place_id"), nullable=False, index=True)
    sequence         = Column(Integer, nullable=False)
    created_at       = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # 기존: Route와의 양방향 매핑
    route = relationship(
        "Route",
        back_populates="places",
    )
    # 기존: Place와의 양방향 매핑
    place = relationship(
        "Place",
        back_populates="route_associations",
    )

class DbTravelRoute(Base):
    __tablename__ = "travel_routes"

    id               = Column(String, primary_key=True, default=generate_uuid, index=True)
    owner_id         = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name             = Column(String, nullable=True)
    description      = Column(Text, nullable=True)
    place_google_ids = Column(
        ARRAY(String),
        nullable=False,
        default=list,
        server_default=expression.text("'{}'"),
    )
    moving_info      = Column(JSON, nullable=False, default=list, server_default=expression.text("'[]'"))
    estimated_duration = Column(String, nullable=True)
    total_distance     = Column(String, nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)