import logging  # 로깅 모듈 import
from typing import Any, List, Optional

import httpx  # Add import for httpx client
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import crud
from app.db import schemas, models
from app.api import deps
from app.services import google_places

router = APIRouter()
logger = logging.getLogger(__name__)  # 로거 인스턴스 생성

# --------------------------------------------------------------------------- #
# 기본 목록 (DB에 저장된 장소 조회)                                            #
# --------------------------------------------------------------------------- #
@router.get("/db/", response_model=List[schemas.Place], tags=["places_db"])
def read_places_from_db(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve places stored in DB."""
    logger.info("Reading places from DB: skip=%s, limit=%s", skip, limit)
    return crud.place.get_multi(db, skip=skip, limit=limit)


# --------------------------------------------------------------------------- #
# Google Nearby Search (주변 장소 검색 및 DB 캐싱)                            #
# --------------------------------------------------------------------------- #
@router.get("/nearby/", response_model=List[schemas.PlaceBase], tags=["places_google"])
async def get_nearby_places(
    *,
    latitude: float = Query(..., description="Center latitude"),
    longitude: float = Query(..., description="Center longitude"),
    radius: int = Query(5_000, description="Search radius (m)"),
    type: Optional[str] = Query(None, description="Optional place type (e.g., restaurant, cafe)"),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Search nearby via Google Places API, returns basic info.
    Checks DB cache first.
    """
    logger.info(
        "Nearby search request: lat=%s, lng=%s, radius=%s, type=%s",
        latitude,
        longitude,
        radius,
        type,
    )
    results = await google_places.search_nearby_places(latitude, longitude, radius, type)

    items: List[schemas.PlaceBase] = []
    for r in results:
        pid = r.get("place_id")
        if not pid:
            continue

        db_place = crud.place.get_by_google_place_id(db, google_place_id=pid)
        if db_place:
            # If in DB, use from_orm (should already have image_url/type if saved)
            items.append(schemas.PlaceBase.from_orm(db_place))
            logger.debug(f"Nearby search: Found place {pid} in DB cache.")
        else:
            # Get photo_reference and type from Google result
            photo_refs = [
                p.get("photo_reference")
                for p in r.get("photos", []) if isinstance(p, dict)
            ]
            image_url = (
                f"/api/v1/places/{pid}/photo" if photo_refs else None
            )
            types = r.get("types", [])
            main_type = types[0] if types else "정보 없음"
            items.append(
                schemas.PlaceBase(
                    google_place_id=pid,
                    name=r.get("name"),
                    address=r.get("vicinity"),
                    latitude=r.get("geometry", {}).get("location", {}).get("lat"),
                    longitude=r.get("geometry", {}).get("location", {}).get("lng"),
                    types=types,
                    type=main_type,
                    rating=r.get("rating"),
                    photo_references=photo_refs or None,
                    image_url=image_url,
                )
            )
            logger.debug(f"Nearby search: Used Google info for place {pid}.")
    logger.info(f"Nearby search completed. Returning {len(items)} places.")
    return items


# --------------------------------------------------------------------------- #
# Google Text Search (텍스트 기반 장소 검색)                                   #
# --------------------------------------------------------------------------- #
@router.get("/search/", response_model=List[schemas.PlaceBase], tags=["places_google"])
async def search_places(
    query: str = Query(..., description="Search query (e.g., '송도 카페')"),
    region: Optional[str] = Query("kr", description="Region bias (e.g., 'kr')"),
    limit: int = Query(20, description="Max results"),
    db: Session = Depends(deps.get_db),
) -> List[schemas.PlaceBase]:
    """Search places using Google Text Search."""
    logger.info(f"Text search request: query='{query}', region='{region}', limit={limit}")
    results = await google_places.search_places_google(query, region=region, limit=limit)

    items: List[schemas.PlaceBase] = []
    for r in results:
        pid = r.get("place_id")
        if not pid:
            continue

        db_place = crud.place.get_by_google_place_id(db, google_place_id=pid)
        if db_place:
            items.append(schemas.PlaceBase.from_orm(db_place))
            logger.debug(f"Text search: Cached place {pid}.")
        else:
            photo_refs = [
                p.get("photo_reference")
                for p in r.get("photos", []) if isinstance(p, dict)
            ]
            image_url = (
                f"/api/v1/places/{pid}/photo" if photo_refs else None
            )
            types = r.get("types", [])
            main_type = types[0] if types else "정보 없음"
            items.append(
                schemas.PlaceBase(
                    google_place_id=pid,
                    name=r.get("name"),
                    address=r.get("formatted_address"),
                    latitude=r.get("geometry", {}).get("location", {}).get("lat"),
                    longitude=r.get("geometry", {}).get("location", {}).get("lng"),
                    types=types,
                    type=main_type,
                    rating=r.get("rating"),
                    photo_references=photo_refs or None,
                    image_url=image_url,
                )
            )
            logger.debug(f"Text search: Used Google info for place {pid}.")
    logger.info(f"Text search completed. Returning {len(items)} places.")
    return items


# --------------------------------------------------------------------------- #
# 상세 정보: ID 기반 (DB 조회 → 없으면 Google Details & 저장)                  #
# --------------------------------------------------------------------------- #
@router.get("/{place_id}", response_model=schemas.Place, tags=["places_db", "places_google"])
async def read_place_by_id(
    *,
    place_id: str = Path(..., description="Google Place ID (e.g., ChIJ...)"),
    db: Session = Depends(deps.get_db),
) -> Any:
    logger.info(f"Reading place details for ID: {place_id}")
    db_place = crud.place.get_by_google_place_id(db, google_place_id=place_id)

    # Always fetch the latest user_ratings_total from Google to get accurate review counts
    total_reviews_count = 0
    try:
        # Make a lightweight call to Google Places API to get just the user_ratings_total
        latest_details = await google_places.get_place_details(
            place_id, 
            fields="user_ratings_total"
        )
        if latest_details and "user_ratings_total" in latest_details:
            total_reviews_count = latest_details["user_ratings_total"]
            logger.info(f"Got total reviews count from Google: {total_reviews_count} for place {place_id}")
    except Exception as e:
        logger.error(f"Failed to get total reviews count from Google: {e}")

    # 1) DB에 없으면 Google API → 저장
    if not db_place:
        detail = await google_places.get_place_details(
            place_id,
            fields=(
                "name,formatted_address,geometry,rating,"
                "user_ratings_total,types,photos,"
                "opening_hours,website,formatted_phone_number,reviews"
            ),
        )
        if not detail:
            raise HTTPException(404, "Place not found")
            
        # If we didn't get total_reviews_count earlier, use the one from detailed request
        if total_reviews_count == 0 and "user_ratings_total" in detail:
            total_reviews_count = detail["user_ratings_total"]
            
        # Get the primary type for this place
        types = detail.get("types", [])
        main_type = ""
        
        # Map common Google place types to Korean descriptions
        type_mapping = {
            "point_of_interest": "관광 명소",
            "tourist_attraction": "관광 명소",
            "establishment": "시설",
            "food": "식당",
            "restaurant": "식당",
            "cafe": "카페",
            "lodging": "숙박",
            "hotel": "호텔",
            "park": "공원",
            "museum": "박물관",
            "shopping_mall": "쇼핑몰",
            "store": "상점"
        }
        
        # Try to find a meaningful type in the list
        for type_name in types:
            if type_name in type_mapping:
                main_type = type_mapping[type_name]
                break
        
        # If no mapping found, use the first type or default
        if not main_type and types:
            main_type = types[0].replace("_", " ").title()
        else:
            main_type = main_type or "기타 장소"  # Default to "Other Place" instead of "No Information"
            
        create_in = schemas.PlaceCreate(
            google_place_id=place_id,
            name=detail.get("name"),
            address=detail.get("formatted_address"),
            latitude=detail.get("geometry", {}).get("location", {}).get("lat"),
            longitude=detail.get("geometry", {}).get("location", {}).get("lng"),
            types=detail.get("types"),
            rating=detail.get("rating"),
            user_ratings_total=detail.get("user_ratings_total"),
            type=main_type,
            photo_references=[
                p["photo_reference"] for p in detail.get("photos", []) if isinstance(p, dict)
            ] or None,
            website=detail.get("website"),
            phone_number=detail.get("formatted_phone_number"),
        )
        try:
            db_place = crud.place.create(db, obj_in=create_in)
            db.refresh(db_place)
            
            # Process Google reviews if available
            google_reviews = detail.get("reviews", [])
            if google_reviews:
                logger.info(f"Found {len(google_reviews)} Google reviews for place {place_id}, saving to database")
                for review_data in google_reviews:
                    try:
                        # Create ReviewCreate object from Google review data
                        review_in = schemas.ReviewCreate(
                            rating=review_data.get("rating", 3),
                            text=review_data.get("text", ""),
                            author_name=review_data.get("author_name", "Google User"),
                            profile_photo_url=review_data.get("profile_photo_url"),
                            relative_time_description=review_data.get("relative_time_description", "")
                        )
                        # Save review with place association but no user_id (Google review)
                        crud.review.create_with_place(
                            db=db, 
                            obj_in=review_in,
                            place_google_id=place_id
                        )
                    except Exception as review_err:
                        logger.error(f"Error saving Google review: {review_err}", exc_info=True)
                        # Continue with next review (don't halt entirely on one review failure)
                        continue
                db.commit()  # Commit all reviews
        except Exception as e:
            logger.error(f"Error creating place: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(500, "Could not save place details")

    # 2) DB에 있으면 부족 정보 업데이트
    else:
        need_detail = db_place.rating is None or not db_place.reviews
        
        # Update the user_ratings_total if we got a new value
        if total_reviews_count > 0 and (db_place.user_ratings_total is None or total_reviews_count != db_place.user_ratings_total):
            upd = schemas.PlaceUpdate(user_ratings_total=total_reviews_count)
            try:
                db_place = crud.place.update(db, db_obj=db_place, obj_in=upd)
                db.refresh(db_place)
                db.commit()
            except Exception as e:
                logger.error(f"Error updating place user_ratings_total: {e}", exc_info=True)
                db.rollback()
        
        if need_detail:
            detail = await google_places.get_place_details(place_id, fields="rating,reviews")
            if detail:
                upd = schemas.PlaceUpdate()
                if detail.get("rating") is not None:
                    upd.rating = detail["rating"]
                    
                # Check for Google reviews and save them if available
                google_reviews = detail.get("reviews", [])
                if google_reviews:
                    logger.info(f"Found {len(google_reviews)} Google reviews for existing place {place_id}, updating database")
                    
                    # Get existing reviews to avoid duplicates
                    existing_reviews = crud.review.get_multi_by_place(db, place_id=place_id)
                    existing_text_set = {r.text for r in existing_reviews if r.text}
                    
                    for review_data in google_reviews:
                        review_text = review_data.get("text", "")
                        
                        # Skip if this review text already exists in the database
                        if review_text and review_text in existing_text_set:
                            continue
                            
                        try:
                            # Create ReviewCreate object from Google review data
                            review_in = schemas.ReviewCreate(
                                rating=review_data.get("rating", 3),
                                text=review_text,
                                author_name=review_data.get("author_name", "Google User"),
                                profile_photo_url=review_data.get("profile_photo_url"),
                                relative_time_description=review_data.get("relative_time_description", "")
                            )
                            # Save review with place association but no user_id (Google review)
                            crud.review.create_with_place(
                                db=db, 
                                obj_in=review_in,
                                place_google_id=place_id
                            )
                        except Exception as review_err:
                            logger.error(f"Error saving Google review: {review_err}", exc_info=True)
                            continue
                
                try:
                    db_place = crud.place.update(db, db_obj=db_place, obj_in=upd)
                    db.refresh(db_place)
                    db.commit()  # Commit any new reviews
                except Exception as e:
                    logger.error(f"Error updating place or reviews: {e}", exc_info=True)
                    db.rollback()

    # 3) plain dict 조립 후 반환
    from app.db.schemas.review import Review as ReviewSchema
    raw_reviews = crud.review.get_multi_by_place(db, place_id=db_place.google_place_id)
    reviews_list = [ReviewSchema.from_orm(r).model_dump() for r in raw_reviews]
    reviews_count = len(reviews_list)
    
    # Use the total reviews count from Google Places API if available
    final_total_count = total_reviews_count or db_place.user_ratings_total or reviews_count
    
    # Use a meaningful place type instead of "정보 없음"
    place_type = getattr(db_place, "type", None)
    if not place_type or place_type == "정보 없음":
        types = getattr(db_place, "types", None) or []
        if types:
            # Same type mapping as above
            type_mapping = {
                "point_of_interest": "관광 명소",
                "tourist_attraction": "관광 명소", 
                "establishment": "시설",
                "food": "식당",
                "restaurant": "식당",
                "cafe": "카페",
                "lodging": "숙박",
                "hotel": "호텔",
                "park": "공원",
                "museum": "박물관",
                "shopping_mall": "쇼핑몰",
                "store": "상점"
            }
            
            for type_name in types:
                if type_name in type_mapping:
                    place_type = type_mapping[type_name]
                    break
            
            if not place_type:
                place_type = types[0].replace("_", " ").title()
        else:
            place_type = "기타 장소"
    
    return {
        "google_place_id": db_place.google_place_id,
        "name": db_place.name,
        "latitude": db_place.latitude,
        "longitude": db_place.longitude,
        "address": db_place.address,
        "rating": db_place.rating or 0.0,
        "user_ratings_total": final_total_count,
        "type": place_type,
        "operating_hours": getattr(db_place, "operating_hours", None) or [],
        "tags": getattr(db_place, "tags", None) or [],
        "image_url": getattr(db_place, "image_url", None),
        "website": getattr(db_place, "website", None),
        "phone_number": getattr(db_place, "phone_number", None),
        "description": getattr(db_place, "description", None),
        "photo_references": getattr(db_place, "photo_references", None) or [],
        "reviews": reviews_list,
        "reviews_count": final_total_count,  # Use the total count here too
    }


# --------------------------------------------------------------------------- #
# Photo Proxy (DB 캐시 → Google 조회 → 이미지 반환)                          #
# --------------------------------------------------------------------------- #
@router.get(
    "/{place_id}/photo",
    response_class=Response,
    tags=["places_db", "places_google"],
)
async def get_place_photo(
    *,
    place_id: str = Path(..., description="Google Place ID"),
    max_width: int = Query(400, description="Max image width"),
    db: Session = Depends(deps.get_db),
) -> Response:
    logger.info(f"Photo request for place={place_id}, max_width={max_width}")
    db_place = crud.place.get_by_google_place_id(db, google_place_id=place_id)

    photo_ref: Optional[str] = None
    if db_place and db_place.photo_references:
        photo_ref = db_place.photo_references[0]

    if not photo_ref:
        detail = await google_places.get_place_details(place_id, fields="photos")
        photos = detail.get("photos") if detail else []
        if photos and isinstance(photos, list):
            photo_ref = photos[0].get("photo_reference")

    if not photo_ref:
        # Instead of 404, return a placeholder image
        logger.info(f"No photo available for place_id={place_id}, returning placeholder")
        # Return a placeholder image or redirect to a default image
        try:
            # Try to use a type-specific placeholder based on place type
            if db_place and db_place.types:
                place_type = next((t for t in db_place.types if t in ["restaurant", "cafe", "park", "hotel", "museum", "shopping_mall"]), "generic")
            else:
                place_type = "generic"
                
            # You can serve placeholder images from a static directory or use a CDN service
            # For now, we'll use a public image placeholder service
            placeholder_url = f"https://placehold.co/600x400/EFEFEF/999999?text=No+Image+Available+({place_type.title()})"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(placeholder_url)
                response.raise_for_status()
                return Response(
                    content=response.content,
                    media_type=response.headers.get("Content-Type", "image/png"),
                    headers={"Cache-Control": "public, max-age=604800"}  # Cache for 7 days
                )
        except Exception as placeholder_err:
            logger.error(f"Error fetching placeholder image: {placeholder_err}")
            # If placeholder fails, then raise 404
            raise HTTPException(404, "No photo_reference available")

    try:
        content, mime = await google_places.get_google_place_photo_direct(photo_ref, max_width)
    except Exception as e:
        raise HTTPException(502, "Failed to fetch image from Google")

    if not content:
        raise HTTPException(502, "Empty image content")

    return Response(content=content, media_type=mime, headers={"Cache-Control": "public, max-age=86400"})


# --------------------------------------------------------------------------- #
# 리뷰 생성 및 조회                                                            #
# --------------------------------------------------------------------------- #
@router.post("/{place_id}/reviews/", response_model=schemas.Review, tags=["reviews"])
def create_review(
    *,
    place_id: str = Path(..., description="Google Place ID"),
    review_in: schemas.ReviewCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    db_place = crud.place.get_by_google_place_id(db, google_place_id=place_id)
    if not db_place:
        raise HTTPException(404, "Place not found")
    try:
        review = crud.review.create_with_user_and_place(
            db=db,
            obj_in=review_in,
            user_id=current_user.id,
            place_google_id=db_place.google_place_id,
        )
    except Exception as e:
        logger.error(f"Error creating review: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(500, "Could not save review")
    return review


@router.get("/{place_id}/reviews/", response_model=List[schemas.Review], tags=["reviews"])
def read_reviews(
    *,
    place_id: str = Path(..., description="Google Place ID"),
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> List[Any]:
    db_place = crud.place.get_by_google_place_id(db, google_place_id=place_id)
    if not db_place:
        logger.warning(f"Place {place_id} not found when attempting to get reviews")
        return []
    # Use place_google_id to match the Review model's field name
    reviews = crud.review.get_multi_by_place(db, place_id=db_place.google_place_id, skip=skip, limit=limit)
    logger.info(f"Retrieved {len(reviews)} reviews for place {place_id}")
    return reviews