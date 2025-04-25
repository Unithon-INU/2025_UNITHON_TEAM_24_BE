# app/crud/crud_route.py

from uuid import uuid4
from typing import Any, Dict, List, Optional
import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import models, schemas


def _serialize_for_db(data: Any) -> Any:
    if isinstance(data, list):
        return [_serialize_for_db(item) for item in data]
    if isinstance(data, dict):
        return {k: _serialize_for_db(v) for k, v in data.items()}
    # Pydantic v2: model_dump
    if hasattr(data, "model_dump"):
        return _serialize_for_db(data.model_dump(mode="python", by_alias=False))
    return data


def create_route(
    db: Session,
    route_data: Dict[str, Any],
    owner_id: str,
) -> models.DbTravelRoute:
    """
    AI/서비스 로직이 만들어 준 route_data(dict)를 DB에 적재하고
    완성된 DbTravelRoute 인스턴스를 반환합니다.
    """
    # 1) moving_info JSON 직렬화
    moving_info_serialized = _serialize_for_db(route_data.get("moving_info", []))

    # 2) 모델 인스턴스 생성
    db_route = models.DbTravelRoute(
        id=str(uuid4()),
        owner_id=owner_id,
        name=route_data.get("name"),
        description=route_data.get("description"),
        place_google_ids=[
            p["google_place_id"]
            for p in route_data.get("places", [])
            if isinstance(p, dict) and p.get("google_place_id")
        ],
        moving_info=moving_info_serialized,
        estimated_duration=route_data.get("estimated_duration"),
        total_distance=route_data.get("total_distance"),
        created_at=datetime.datetime.utcnow(),
    )

    # 3) INSERT
    db.add(db_route)
    try:
        db.commit()
        db.refresh(db_route)
        print(f"[crud_route] Route saved → id={db_route.id}")
    except Exception as exc:
        db.rollback()
        print(f"[crud_route] ERROR saving route: {exc}")
        raise

    return db_route


def get_routes_by_owner(
    db: Session,
    owner_id: str,
    skip: int = 0,
    limit: int = 100,
) -> List[models.DbTravelRoute]:
    return (
        db.query(models.DbTravelRoute)
        .filter(models.DbTravelRoute.owner_id == owner_id)
        .order_by(desc(models.DbTravelRoute.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_route_by_id(
    db: Session,
    route_id: str,
    owner_id: str,
) -> Optional[models.DbTravelRoute]:
    return (
        db.query(models.DbTravelRoute)
        .filter(
            models.DbTravelRoute.id == route_id,
            models.DbTravelRoute.owner_id == owner_id,
        )
        .first()
    )


def get_without_owner_check(
    db: Session, 
    route_id: str
) -> Optional[models.DbTravelRoute]:
    """
    소유자 확인 없이 경로 조회 (공개 경로용)
    route_id만으로 경로를 조회합니다.
    """
    return (
        db.query(models.DbTravelRoute)
        .filter(models.DbTravelRoute.id == route_id)
        .first()
    )


async def update_route(
    db: Session,
    route_id: str,
    owner_id: str,
    route_update: schemas.TravelRouteUpdate,
) -> Optional[models.DbTravelRoute]:
    db_route = get_route_by_id(db, route_id, owner_id)
    if not db_route:
        return None

    patch = route_update.model_dump(exclude_unset=True)
    # TODO: recalc moving_info if places changed

    for key, value in patch.items():
        setattr(db_route, key, _serialize_for_db(value) if isinstance(value, (dict, list)) else value)

    db.add(db_route)
    try:
        db.commit()
        db.refresh(db_route)
        print(f"[crud_route] Route updated → id={db_route.id}")
    except Exception as exc:
        db.rollback()
        print(f"[crud_route] ERROR updating route: {exc}")
        raise

    return db_route


def delete_route(
    db: Session,
    route_id: str,
    owner_id: str,
) -> bool:
    db_route = get_route_by_id(db, route_id, owner_id)
    if not db_route:
        return False
    try:
        db.delete(db_route)
        db.commit()
        print(f"[crud_route] Route deleted → id={route_id}")
        return True
    except Exception as exc:
        db.rollback()
        print(f"[crud_route] ERROR deleting route: {exc}")
        return False