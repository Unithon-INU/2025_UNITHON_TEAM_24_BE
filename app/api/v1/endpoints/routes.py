# app/api/v1/endpoints/routes.py

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app import crud
from app.db import models, schemas
from app.api import deps
from app.services.route_generator import generate_route_logic

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/generate",
    response_model=schemas.TravelRoute,
    status_code=status.HTTP_201_CREATED,
    tags=["routes"],
)
async def generate_route(
    *,
    pref_in: schemas.TravelPreferenceCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    1) AI 경로생성 로직(generate_route_logic)으로 dict 획득
    2) dict → TravelRouteCreate 스키마 변환
    3) DB에 저장(persist)
    4) 저장된 ORM 객체 + 실제 Place 리스트를 모아서 응답
    """
    # 1) 로직 실행
    try:
        route_dict: Dict[str, Any] = await generate_route_logic(pref_in, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[generate_route] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal route generation error")

    # 2) TravelRouteCreate 스키마로 변환
    try:
        create_in = schemas.TravelRouteCreate(
            name=route_dict["name"],
            description=route_dict["description"],
            places=[schemas.PlaceRef(google_place_id=p["google_place_id"]) for p in route_dict["places"]],
            moving_info=route_dict.get("moving_info", []),
            estimated_duration=route_dict.get("estimated_duration"),
            total_distance=route_dict.get("total_distance"),
        )
    except KeyError as e:
        logger.error(f"[generate_route] Missing key in route_dict: {e}")
        raise HTTPException(status_code=500, detail="Malformed route data")

    # 3) DB에 저장
    try:
        # Pydantic 객체를 일반 dict로 변환
        route_data = create_in.model_dump(mode="python")
        new_route = crud.route.create(
            db=db,
            route_data=route_data,
            owner_id=current_user.id,
        )
        db.refresh(new_route)
    except Exception as e:
        logger.error(f"[generate_route] DB save failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to persist generated route")

    # 4) place_google_ids로 실제 Place 레코드 조회 → Pydantic 변환
    places = []
    for pid in new_route.place_google_ids:
        p = crud.place.get_by_google_place_id(db, google_place_id=pid)
        if p:
            # Handle reviews properly by converting them to dictionaries first
            raw_reviews = crud.review.get_multi_by_place(db, place_id=p.google_place_id)
            reviews_list = [schemas.review.Review.from_orm(r).model_dump() for r in raw_reviews]
            
            # Create place data with reviews correctly included
            place_data = {
                "google_place_id": p.google_place_id,
                "name": p.name,
                "address": p.address,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "types": p.types,
                "type": getattr(p, "type", None) or "정보 없음",
                "rating": p.rating or 0.0,
                "photo_references": p.photo_references or [],
                "image_url": getattr(p, "image_url", None),
                "reviews": reviews_list,
                "operating_hours": getattr(p, "operating_hours", None) or [],
                "tags": getattr(p, "tags", None) or [],
                "description": getattr(p, "description", None),
            }
            places.append(schemas.Place(**place_data))

    # 5) 최종 TravelRoute 응답 생성
    response = schemas.TravelRoute(
        id=new_route.id,
        owner_id=new_route.owner_id,
        name=new_route.name,
        description=new_route.description,
        place_google_ids=new_route.place_google_ids,
        moving_info=new_route.moving_info,
        estimated_duration=new_route.estimated_duration,
        total_distance=new_route.total_distance,
        created_at=new_route.created_at,
        places=places,
    )
    return response


@router.get(
    "/",
    response_model=List[schemas.TravelRoute],
    status_code=status.HTTP_200_OK,
    tags=["routes"],
)
def read_routes(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 50,
) -> Any:
    # 마찬가지로 read 시에도 places 필드를 채워야 하는 경우 동일한 방식을 적용하세요.
    db_routes = crud.route.get_multi_by_user(db=db, owner_id=current_user.id, skip=skip, limit=limit)
    result: List[schemas.TravelRoute] = []
    for rt in db_routes:
        # Place 조회 및 변환
        places = []
        for pid in rt.place_google_ids:
            p = crud.place.get_by_google_place_id(db, google_place_id=pid)
            if p:
                # Handle reviews properly by converting them to dictionaries first
                raw_reviews = crud.review.get_multi_by_place(db, place_id=p.google_place_id)
                reviews_list = [schemas.review.Review.from_orm(r).model_dump() for r in raw_reviews]
                
                # Use the user_ratings_total field from the database if available
                reviews_count = getattr(p, "user_ratings_total", None) or len(reviews_list)
                
                # Create place data with reviews correctly included
                place_data = {
                    "google_place_id": p.google_place_id,
                    "name": p.name,
                    "address": p.address,
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "types": p.types,
                    "type": getattr(p, "type", None) or "기타 장소", # Changed from "정보 없음" to "기타 장소"
                    "rating": p.rating or 0.0,
                    "photo_references": p.photo_references or [],
                    "image_url": getattr(p, "image_url", None),
                    "reviews": reviews_list,
                    "reviews_count": reviews_count,  # Add the reviews count
                    "user_ratings_total": getattr(p, "user_ratings_total", None) or reviews_count,
                    "operating_hours": getattr(p, "operating_hours", None) or [],
                    "tags": getattr(p, "tags", None) or [],
                    "description": getattr(p, "description", None),
                }
                places.append(schemas.Place(**place_data))
        
        result.append(schemas.TravelRoute(
            id=rt.id,
            owner_id=rt.owner_id,
            name=rt.name or "이름 없음",  # <-- fallback for None
            description=rt.description or "",
            place_google_ids=rt.place_google_ids,
            moving_info=rt.moving_info,
            estimated_duration=rt.estimated_duration,
            total_distance=rt.total_distance,
            created_at=rt.created_at,
            places=places,
        ))
    return result


@router.get(
    "/{route_id}",
    response_model=schemas.TravelRoute,
    status_code=status.HTTP_200_OK,
    tags=["routes"],
)
def read_route(
    *,
    route_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    db_route = crud.route.get(db=db, route_id=route_id, owner_id=current_user.id)
    if not db_route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Include reviews for each place
    places = []
    for pid in db_route.place_google_ids:
        p = crud.place.get_by_google_place_id(db, google_place_id=pid)
        if p:
            # Get reviews for this place
            raw_reviews = crud.review.get_multi_by_place(db, place_id=p.google_place_id)
            reviews_list = [schemas.review.Review.from_orm(r).model_dump() for r in raw_reviews]
            
            # Use the user_ratings_total field from the database if available
            reviews_count = getattr(p, "user_ratings_total", None) or len(reviews_list)
            
            # Create place data with reviews correctly included
            place_data = {
                "google_place_id": p.google_place_id,
                "name": p.name,
                "address": p.address,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "types": p.types,
                "type": getattr(p, "type", None) or "기타 장소",  # Changed from "정보 없음" to "기타 장소"
                "rating": p.rating or 0.0,
                "photo_references": p.photo_references or [],
                "image_url": getattr(p, "image_url", None),
                "reviews": reviews_list,
                "reviews_count": reviews_count,  # Add the reviews count
                "user_ratings_total": getattr(p, "user_ratings_total", None) or reviews_count,  # Add total ratings
                "operating_hours": getattr(p, "operating_hours", None) or [],
                "tags": getattr(p, "tags", None) or [],
                "description": getattr(p, "description", None),
            }
            places.append(schemas.Place(**place_data))

    return schemas.TravelRoute(
        id=db_route.id,
        owner_id=db_route.owner_id,
        name=db_route.name,
        description=db_route.description,
        place_google_ids=db_route.place_google_ids,
        moving_info=db_route.moving_info,
        estimated_duration=db_route.estimated_duration,
        total_distance=db_route.total_distance,
        created_at=db_route.created_at,
        places=places,
    )


@router.put(
    "/{route_id}",
    response_model=schemas.TravelRoute,
    status_code=status.HTTP_200_OK,
    tags=["routes"],
)
def update_route(
    *,
    route_id: str,
    route_in: schemas.TravelRouteUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    db_route = crud.route.get(db=db, route_id=route_id, owner_id=current_user.id)
    if not db_route:
        raise HTTPException(status_code=404, detail="Route not found")

    try:
        updated = crud.route.update(
            db=db,
            route_id=route_id,
            owner_id=current_user.id,
            route_update=route_in,
        )
        db.refresh(updated)
    except Exception as e:
        logger.error(f"[update_route] DB update failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update route")

    # 수정된 결과에도 places 채워서 반환
    places = []
    for pid in updated.place_google_ids:
        p = crud.place.get_by_google_place_id(db, google_place_id=pid)
        if p:
            # Handle reviews properly by converting them to dictionaries first
            raw_reviews = crud.review.get_multi_by_place(db, place_id=p.google_place_id)
            reviews_list = [schemas.review.Review.from_orm(r).model_dump() for r in raw_reviews]
            
            # Create place data with reviews correctly included
            place_data = {
                "google_place_id": p.google_place_id,
                "name": p.name,
                "address": p.address,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "types": p.types,
                "type": getattr(p, "type", None) or "정보 없음",
                "rating": p.rating or 0.0,
                "photo_references": p.photo_references or [],
                "image_url": getattr(p, "image_url", None),
                "reviews": reviews_list,
                "operating_hours": getattr(p, "operating_hours", None) or [],
                "tags": getattr(p, "tags", None) or [],
                "description": getattr(p, "description", None),
            }
            places.append(schemas.Place(**place_data))
            
    return schemas.TravelRoute(
        id=updated.id,
        owner_id=updated.owner_id,
        name=updated.name,
        description=updated.description,
        place_google_ids=updated.place_google_ids,
        moving_info=updated.moving_info,
        estimated_duration=updated.estimated_duration,
        total_distance=updated.total_distance,
        created_at=updated.created_at,
        places=places,
    )


@router.delete(
    "/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "No Content"},
        404: {"description": "Route not found"},
    },
    tags=["routes"],
)
def delete_route(
    *,
    route_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> None:
    """
    TravelRoute 삭제
    - 204: 삭제 성공 (본문 없음)
    - 404: 경로가 없거나 삭제 실패
    """
    success = crud.route.remove(db=db, route_id=route_id, owner_id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found or delete failed")
    return Response(status_code=status.HTTP_204_NO_CONTENT)