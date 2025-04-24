# app/services/route_generator.py

from __future__ import annotations

import logging
import random  # 향후 다양화 로직용
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.db import models, schemas
from app.db.schemas.preference import TravelPreferenceCreate
from app.services import google_places

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────
# 가중치 & 타입‑카테고리 매핑
# ────────────────────────────────────────────
WEIGHTS: Dict[str, float] = {
    "rating": 0.4,
    "distance": 0.3,     # ✔️ 실제 거리계산 로직 없음 → 고정값
    "type_match": 0.3,
}

PLACE_TYPE_MAPPING: Dict[str, List[str]] = {
    "cafe": ["cafe"],
    "restaurant": ["restaurant", "food"],
    "bar": ["bar"],
    "park": ["park"],
    "museum": ["museum", "tourist_attraction"],
    "art_gallery": ["art_gallery", "tourist_attraction"],
    "shopping_mall": ["shopping_mall", "store"],
    "point_of_interest": ["point_of_interest", "establishment"],
}

# ────────────────────────────────────────────
# 내부 헬퍼
# ────────────────────────────────────────────
def _map_google_type_to_category(google_types: List[str]) -> Optional[str]:
    """Google type → 당사 카테고리 1개 매핑"""
    if not google_types:
        return None
    for category, gtypes in PLACE_TYPE_MAPPING.items():
        if any(t in google_types for t in gtypes):
            return category
    return google_types[0]

def _calculate_score(
    place_data: Dict[str, Any],
    preferences: TravelPreferenceCreate,
    origin_lat: float,
    origin_lon: float,
) -> float:
    """단순 Heuristic Score"""
    score = 0.0
    # ① 별점
    rating = float(place_data.get("rating") or 0.0)
    score += WEIGHTS["rating"] * (rating / 5.0)
    # ② 거리 (여기서는 고정 0.8)
    score += WEIGHTS["distance"] * 0.8
    # ③ 스타일 매치
    place_cat = _map_google_type_to_category(place_data.get("types", []))
    if place_cat and preferences.preferred_styles and place_cat in preferences.preferred_styles:
        score += WEIGHTS["type_match"]
    return score

# ────────────────────────────────────────────
# Google API 응답 → Pydantic Place 스키마 변환
# ────────────────────────────────────────────
def _convert_google_place_to_schema(data: Dict[str, Any]) -> Optional[schemas.Place]:
    """
    Google Places API 응답 → Pydantic Place 스키마 변환
    * 반드시 `schemas.Place` 로 변환하여 google_place_id 포함
    """
    try:
        pid   = data.get("place_id")
        name  = data.get("name")
        loc   = data.get("geometry", {}).get("location", {})
        lat   = loc.get("lat")
        lng   = loc.get("lng")
        if not all([pid, name, lat, lng]):
            logger.warning("필수 누락 → skip  : %s", pid)
            return None

        # photo references
        photo_refs = [
            p["photo_reference"]
            for p in (data.get("photos") or [])
            if isinstance(p, dict) and p.get("photo_reference")
        ]

        # opening_hours.weekday_text 가 리스트이므로 무조건 List[str]
        opening_hours = []
        if isinstance(data.get("opening_hours"), dict):
            wh = data["opening_hours"].get("weekday_text")
            if isinstance(wh, list):
                opening_hours = wh

        place_dict: Dict[str, Any] = {
            "google_place_id":     pid,
            "name":                name,
            "latitude":            lat,
            "longitude":           lng,
            "address":             data.get("formatted_address") or data.get("vicinity"),
            "rating":              data.get("rating"),
            # 구글 키 이름에 맞춰 변경
            "user_ratings_total":  data.get("user_ratings_total"),
            "types":               data.get("types") or [],
            "photo_references":    photo_refs,
            "website":             data.get("website"),
            "phone_number":        data.get("formatted_phone_number"),
            "description":         None,
            "type":                _map_google_type_to_category(data.get("types", [])),
            "operating_hours":     opening_hours,
            "image_url":           None,
            "tags":                data.get("types") or [],
            "reviews":             [],
        }

        # Pydantic V2: Place 모델로 검증 및 변환
        return schemas.Place.model_validate(place_dict)

    except Exception as e:
        logger.error("Convert error %s – %s", data.get("place_id"), e, exc_info=True)
        return None

# ────────────────────────────────────────────
# public: 경로 생성 메인
# ────────────────────────────────────────────
async def generate_route_logic(
    preferences: TravelPreferenceCreate,
    db: Session,
    current_user: models.User,
) -> Dict[str, Any]:
    """
    • Google Places 에서 장소 검색  
    • 점수 상위 5개 선택  
    • ‘경로 dict’(DB 저장 전용) 반환
    """
    logger.info("▶ route_generator: user=%s", current_user.id)
    origin_lat = preferences.latitude or 37.3949
    origin_lon = preferences.longitude or 126.6516
    search_types = preferences.preferred_styles or ["point_of_interest"]

    # 1) 검색
    raw_places: List[Dict[str, Any]] = []
    for t in search_types:
        try:
            raw_places.extend(
                await google_places.search_nearby_places(origin_lat, origin_lon, radius=5000, place_type=t)
            )
        except Exception as exc:
            logger.error("Google Places 호출 오류: %s", exc, exc_info=True)
            raise HTTPException(503, "Failed to query Google Places API")
    if not raw_places:
        raise HTTPException(400, "No suitable places found nearby.")

    # 2) 스코어링
    scored: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_places:
        pid = raw.get("place_id")
        if not pid or pid in seen:
            continue
        place_obj = _convert_google_place_to_schema(raw)
        if not place_obj:
            continue

        # DB 캐시: crud.place.create/update 로 저장 시도 (생략)
        if not crud.place.get_by_google_place_id(db, pid):
            try:
                crud.place.create(db, obj_in=schemas.PlaceCreate.model_validate({
                    **place_obj.model_dump(mode="python", by_alias=True),
                    # PlaceCreate 에 필요한 필드만 남기려면 exclude_unset 등 사용
                }))
            except Exception:
                pass

        score = _calculate_score(raw, preferences, origin_lat, origin_lon)
        scored.append({"place_obj": place_obj, "score": score})
        seen.add(pid)

    # 정렬 & 상위 5개
    scored.sort(key=lambda x: x["score"], reverse=True)
    top5 = scored[:5]

    if len(top5) < 3:
        raise HTTPException(400, "Not enough suitable places found.")

    # 3) 최종 반환 dict
    return {
        "name": f"{(preferences.preferred_styles or ['추천'])[0]} 경로",
        "description": f"{preferences.budget} 예산, {', '.join(preferences.preferred_styles or [])} 스타일",
        # Place 객체에서 google_place_id 만 뽑아서 plain dict 로
        "places": [{"google_place_id": entry["place_obj"].google_place_id} for entry in top5],
        "moving_info": [],
        "estimated_duration": "정보 없음",
        "total_distance": "정보 없음",
    }