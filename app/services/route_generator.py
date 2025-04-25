# app/services/route_generator.py

from __future__ import annotations

import logging
import random  # 향후 다양화 로직용
import datetime
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
    "rating": 0.3,       # 0.4에서 0.3으로 줄여서 별점 영향력 감소
    "distance": 0.3,     # ✔️ 실제 거리계산 로직 없음 → 고정값
    "type_match": 0.4,   # 0.3에서 0.4로 증가해서 사용자 선호도 중요성 강화
}

# 한국어 스타일 → Google Places API 타입 매핑 추가
KOREAN_STYLE_TO_PLACE_TYPE = {
    "문화탐방": ["museum", "art_gallery", "tourist_attraction", "history_museum"],
    "미식": ["restaurant", "cafe", "bakery", "food"],
    "관광": ["tourist_attraction", "point_of_interest", "landmark"],
    "쇼핑": ["shopping_mall", "store", "clothing_store", "department_store"],
    "휴양": ["park", "spa", "natural_feature", "campground"],
    # 기본값도 추가 (여러 일반적인 카테고리)
    "추천": ["tourist_attraction", "point_of_interest", "restaurant", "cafe", "park"]
}

PLACE_TYPE_MAPPING: Dict[str, List[str]] = {
    "cafe": ["cafe"],
    "restaurant": ["restaurant", "food"],
    "bar": ["bar", "night_club"],
    "park": ["park", "natural_feature"],
    "museum": ["museum", "tourist_attraction"],
    "art_gallery": ["art_gallery", "tourist_attraction"],
    "shopping_mall": ["shopping_mall", "store", "clothing_store"],
    "point_of_interest": ["point_of_interest", "establishment"],
    # 추가 카테고리
    "historic": ["historic_site", "landmark", "castle", "church"],
    "outdoor": ["park", "natural_feature", "campground", "zoo", "amusement_park"],
    "entertainment": ["movie_theater", "bowling_alley", "stadium", "aquarium", "zoo"],
    "cultural": ["museum", "art_gallery", "library"],
}

# 추천 다양성을 위한 카테고리 그룹
CATEGORY_GROUPS = {
    "food_drink": ["cafe", "restaurant", "bar"],
    "culture": ["museum", "art_gallery", "historic"],
    "outdoor": ["park", "outdoor"],
    "shopping": ["shopping_mall"],
    "entertainment": ["entertainment"]
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
    # ④ 약간의 랜덤성 추가 (0.0~0.2)
    score += random.random() * 0.2
    return score

def _ensure_category_diversity(scored_places: List[Dict[str, Any]], min_places: int = 7) -> List[Dict[str, Any]]:
    """
    카테고리 다양성을 보장하는 장소 선택 로직
    - 가능한 한 다양한 카테고리의 장소를 포함하려고 시도
    - 최소 장소 수를 5에서 7로 증가
    """
    if len(scored_places) <= min_places:
        return scored_places

    # 장소 스코어로 정렬
    scored_places.sort(key=lambda x: x["score"], reverse=True)
    
    # 카테고리별 그룹화
    category_groups = {}
    for place in scored_places:
        place_obj = place["place_obj"]
        # 'type' 대신 'place_type' 사용 (별도 저장된 변수)
        place_type = place.get("type", "other")
        
        # 어떤 그룹에 속하는지 확인
        group_name = None
        for group, categories in CATEGORY_GROUPS.items():
            if place_type in categories:
                group_name = group
                break
        
        if group_name is None:
            group_name = "other"
            
        if group_name not in category_groups:
            category_groups[group_name] = []
            
        category_groups[group_name].append(place)
    
    # 다양한 카테고리에서 장소 선택
    result = []
    remaining_slots = min_places
    
    # 각 그룹에서 최소 1개씩 선택 (가능한 경우)
    for group_name, places in category_groups.items():
        if places and remaining_slots > 0:
            # 각 그룹에서 최고 점수 장소 선택
            result.append(places[0])
            # 가능하다면 그룹당 두 번째 장소도 추가
            if len(places) > 1 and remaining_slots > 1:
                result.append(places[1])
                remaining_slots -= 1
            remaining_slots -= 1
    
    # 남은 자리는 아직 선택되지 않은 상위 점수 장소로 채움
    if remaining_slots > 0:
        # 이미 선택된 장소 ID 목록
        selected_ids = {place["place_obj"].google_place_id for place in result}
        
        # 아직 선택되지 않은 상위 점수 장소 추가
        for place in scored_places:
            if place["place_obj"].google_place_id not in selected_ids and remaining_slots > 0:
                result.append(place)
                remaining_slots -= 1
                
    # 점수별로 다시 정렬
    result.sort(key=lambda x: x["score"], reverse=True)
    return result

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

        # 카테고리 매핑 (별도 변수로 저장하여 나중에 활용)
        category_type = _map_google_type_to_category(data.get("types", []))

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
            # "type" 필드는 DB에 없으므로 제외
            "operating_hours":     opening_hours,
            "image_url":           None,
            "tags":                data.get("types") or [],
            "reviews":             [],
        }

        # Pydantic V2: Place 모델로 검증 및 변환
        place = schemas.Place.model_validate(place_dict)
        
        # type 정보는 setattr 대신 별도 반환 데이터로 처리 (주석 처리)
        # setattr(place, "type", category_type)
        
        # 원래의 place 객체와 함께 카테고리 타입을 딕셔너리로 반환
        return place

    except Exception as e:
        logger.error("Convert error %s – %s", data.get("place_id"), e, exc_info=True)
        return None

# ────────────────────────────────────────────
# 경로 이동 정보 생성 함수
# ────────────────────────────────────────────
async def _generate_moving_info(places, preferences):
    """
    Google Directions API를 사용하여 장소 간 상세 이동 정보 생성
    - 실제 길찾기 결과로 경로 표시
    - 이동 시간, 거리, 이동 방법, 아이콘 등을 포함
    """
    moving_info = []
    
    if len(places) < 2:
        return moving_info
    
    # 인접한 장소 간의 이동 정보 생성
    for i in range(len(places) - 1):
        start_place = places[i]["place_obj"]
        end_place = places[i+1]["place_obj"]
        
        start_lat, start_lng = start_place.latitude, start_place.longitude
        end_lat, end_lng = end_place.latitude, end_place.longitude
        
        # 두 지점 간 거리 계산 (Haversine formula)
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # 지구 반경(km)
        dlat = radians(end_lat - start_lat)
        dlng = radians(end_lng - start_lng)
        a = sin(dlat/2)**2 + cos(radians(start_lat)) * cos(radians(end_lat)) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance_km = R * c
        
        # 거리에 따른 이동 수단 선택
        if distance_km < 0.8:
            transport_mode = "walking"  # 도보
        elif distance_km < 3:
            transport_mode = "transit"  # 대중교통 또는 도보
        else:
            transport_mode = "transit"  # 대중교통
        
        # Google Directions API 호출
        try:
            directions_data = await google_places.get_directions(
                start_lat, start_lng, 
                end_lat, end_lng,
                mode=transport_mode
            )
            
            if directions_data and "routes" in directions_data and directions_data["routes"]:
                route = directions_data["routes"][0]
                legs = route["legs"][0]
                
                # API에서 가져온 거리 및 소요시간
                distance = legs.get("distance", {}).get("text", f"{distance_km:.1f}km")
                duration = legs.get("duration", {}).get("text", f"{int(distance_km * 15)}분")
                
                # 이동 경로 단계별 안내
                steps = []
                for step in legs.get("steps", []):
                    # HTML 태그 제거
                    import re
                    instruction = re.sub(r'<[^>]+>', '', step.get("html_instructions", ""))
                    
                    # 이동 단계 정보 저장
                    travel_mode = step.get("travel_mode", "").lower()
                    icon = ""
                    
                    # 이동 수단에 따른 아이콘 선택
                    if travel_mode == "walking":
                        icon = "🚶"
                    elif travel_mode == "transit":
                        if "transit_details" in step:
                            transit_type = step["transit_details"].get("line", {}).get("vehicle", {}).get("type", "").lower()
                            if transit_type == "bus":
                                icon = "🚌"
                            elif transit_type in ["subway", "train"]:
                                icon = "🚆"
                            else:
                                icon = "🚇"
                        else:
                            icon = "🚇"
                    elif travel_mode == "driving":
                        icon = "🚗"
                    elif travel_mode == "bicycling":
                        icon = "🚲"
                    else:
                        icon = "➡️"
                        
                    step_distance = step.get("distance", {}).get("text", "")
                    step_duration = step.get("duration", {}).get("text", "")
                    
                    steps.append({
                        "instruction": instruction,
                        "distance": step_distance,
                        "duration": step_duration,
                        "travel_mode": travel_mode,
                        "icon": icon,
                        "polyline": step.get("polyline", {}).get("points", "")
                    })
                
                summary = f"{icon} {start_place.name}에서 {end_place.name}까지 {distance} ({duration})"
                
                info = {
                    "from_place_id": start_place.google_place_id,
                    "to_place_id": end_place.google_place_id,
                    "from_place_name": start_place.name,  # 이름 추가 
                    "to_place_name": end_place.name,      # 이름 추가
                    "transport_mode": transport_mode,
                    "distance": distance,
                    "duration": duration,
                    "summary": summary,
                    "steps": steps,
                    "polyline": route.get("overview_polyline", {}).get("points", "")
                }
                moving_info.append(info)
            else:
                # API 응답이 없는 경우 기본 정보 제공
                if transport_mode == "walking":
                    icon = "🚶"
                elif transport_mode == "transit":
                    icon = "🚇"
                else:
                    icon = "➡️"
                    
                distance_text = f"{distance_km:.1f}km"
                duration_text = f"{int(distance_km * 15)}분"  # 대략적인 소요시간 계산
                
                info = {
                    "from_place_id": start_place.google_place_id,
                    "to_place_id": end_place.google_place_id,
                    "from_place_name": start_place.name,  # 이름 추가
                    "to_place_name": end_place.name,      # 이름 추가
                    "transport_mode": transport_mode,
                    "distance": distance_text,
                    "duration": duration_text,
                    "summary": f"{icon} {start_place.name}에서 {end_place.name}까지 {distance_text} ({duration_text})",
                    "steps": []
                }
                moving_info.append(info)
                
        except Exception as e:
            logger.error(f"Error fetching directions: {e}")
            # 에러 발생 시 기본 이동 정보 제공
            if distance_km < 0.8:
                icon = "🚶"  # 도보
                transport_mode = "walking"
                minutes = max(5, round(distance_km / 4 * 60))
            else:
                icon = "🚇"  # 대중교통
                transport_mode = "transit"
                minutes = round(distance_km / 20 * 60 + 10)
                
            distance_text = f"{distance_km:.1f}km"
            duration_text = f"{minutes}분"
                
            info = {
                "from_place_id": start_place.google_place_id,
                "to_place_id": end_place.google_place_id,
                "from_place_name": start_place.name,  # 이름 추가
                "to_place_name": end_place.name,      # 이름 추가
                "transport_mode": transport_mode,
                "distance": distance_text,
                "duration": duration_text,
                "summary": f"{icon} {start_place.name}에서 {end_place.name}까지 {distance_text} ({duration_text})",
                "steps": []
            }
            moving_info.append(info)
    
    return moving_info

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
    • 다양성을 극대화한 장소 선택
    • '경로 dict'(DB 저장 전용) 반환
    """
    logger.info("▶ route_generator: user=%s", current_user.id)
    logger.info(f"▶ preferences: region={preferences.region}, styles={preferences.preferred_styles}, coords=({preferences.latitude}, {preferences.longitude})")
    
    # 매번 기준 좌표를 약간씩 다르게 설정하여 다양한 결과 도출
    base_lat = preferences.latitude or 37.3949
    base_lon = preferences.longitude or 126.6516
    jitter = 0.003  # 약간 더 좁은 반경 내 랜덤 변동 (약 300m)
    origin_lat = base_lat + (random.random() * jitter * 2 - jitter)
    origin_lon = base_lon + (random.random() * jitter * 2 - jitter)
    
    # 한국어 스타일을 Google Places API 타입으로 변환
    search_types = []
    preferred_styles = preferences.preferred_styles or ["추천"]
    
    for style in preferred_styles:
        # 한국어 스타일에서 Google Places API 타입으로 매핑
        if style in KOREAN_STYLE_TO_PLACE_TYPE:
            search_types.extend(KOREAN_STYLE_TO_PLACE_TYPE[style])
        else:
            # 알 수 없는 스타일은 기본 타입 사용
            search_types.extend(KOREAN_STYLE_TO_PLACE_TYPE["추천"])
    
    # 중복 제거
    search_types = list(set(search_types))
    logger.info(f"▶ Converted styles to search_types: {search_types}")
    
    # 기본 카테고리 항상 추가 - 필수 카테고리
    essential_types = ["tourist_attraction", "point_of_interest"]
    for t in essential_types:
        if t not in search_types:
            search_types.append(t)
            
    # 추가 다양성을 위해 랜덤하게 2-3개 카테고리 더 추가
    extra_categories = ["restaurant", "cafe", "museum", "park", "shopping_mall", "art_gallery"]
    random.shuffle(extra_categories)
    for cat in extra_categories[:random.randint(2, 3)]:
        if cat not in search_types:
            search_types.append(cat)
    
    # 검색 반경을 증가하여 더 많은 장소 검색
    base_radius = 5000  # 이전: 3000
    search_radius = random.randint(base_radius - 500, base_radius + 1000)
    
    # 임시 변수로 시드값 저장 (같은 시드로 계속 요청하는 것 방지)
    timestamp_seed = int(datetime.datetime.now().timestamp())
    random.seed(timestamp_seed + hash(str(current_user.id)) % 10000)

    # 1) 검색
    raw_places: List[Dict[str, Any]] = []
    
    # 지역명을 최우선으로 사용하여 검색 시도 (추가된 코드)
    if preferences.region:
        logger.info(f"First trying text search with region: {preferences.region}")
        for t in search_types[:5]:  # 상위 5개 타입만 사용
            try:
                text_query = f"{preferences.region} {t}"
                logger.info(f"Text search query: {text_query}")
                
                text_places = await google_places.search_places_google(
                    query=text_query, 
                    region="kr", 
                    limit=20  # 더 많은 결과 요청
                )
                
                # 검색 결과가 있으면 추가
                if text_places:
                    logger.info(f"Text search found {len(text_places)} places for '{text_query}'")
                    raw_places.extend(text_places)
            except Exception as e:
                logger.error(f"Text search failed for {text_query}: {e}")
    
    # 기존 검색 로직으로 계속 진행
    for t in search_types:
        try:
            # 카테고리별로 살짝 다른 반경 적용
            category_radius = search_radius + random.randint(-500, 500)
            logger.info(f"Searching category: {t} with radius: {category_radius}")
            
            places_found = await google_places.search_nearby_places(
                origin_lat, origin_lon, 
                radius=category_radius, 
                place_type=t
            )
            
            # 검색 결과가 너무 적은 경우 반경 확장 시도
            if len(places_found) < 3:
                expanded_radius = category_radius + 5000  # 검색 반경 5km 추가
                logger.info(f"Expanding search for {t} with radius: {expanded_radius}")
                expanded_places = await google_places.search_nearby_places(
                    origin_lat, origin_lon, 
                    radius=expanded_radius,
                    place_type=t
                )
                places_found.extend(expanded_places)
                
            # 검색 결과가 여전히 없다면 텍스트 검색 시도 (지역 + 카테고리)
            if len(places_found) < 2:
                logger.info(f"Trying text search for {preferences.region} {t}")
                # 지역명이 있는 경우 텍스트 검색으로 장소 찾기
                if preferences.region:
                    text_query = f"{preferences.region} {t}"
                    text_places = await google_places.search_places_google(
                        query=text_query, 
                        region="kr", 
                        limit=10
                    )
                    places_found.extend(text_places)
                
            # 최대 15개만 추가 (이전: 10개)
            if places_found:
                # 검색 결과 무작위 셔플
                random.shuffle(places_found)
                raw_places.extend(places_found[:min(15, len(places_found))])
                logger.info(f"Found {len(places_found)} places for {t}, total so far: {len(raw_places)}")
                
        except Exception as exc:
            logger.error("Google Places 호출 오류: %s", exc, exc_info=True)
    
    # 최종 검색 결과가 없는 경우 - 백업 데이터 사용
    if not raw_places:
        logger.warning("No places found, using backup data...")
        
        # 백업 데이터: 지역에 따른 대표적인 관광지/장소 미리 정의
        backup_places = {
            "서울": [
                {"place_id": "ChIJzWXFYYuifDUR2yv2ykkTJyY", "name": "남산서울타워", "type": "tourist_attraction", 
                 "latitude": 37.5511, "longitude": 126.9882, "rating": 4.5},
                {"place_id": "ChIJ81VqJSujfDUR8V6l_Usidr0", "name": "경복궁", "type": "tourist_attraction", 
                 "latitude": 37.5796, "longitude": 126.9770, "rating": 4.6},
                {"place_id": "ChIJM_YhNKejfDURuI4Gp1sWeyo", "name": "광화문광장", "type": "tourist_attraction", 
                 "latitude": 37.5724, "longitude": 126.9768, "rating": 4.4},
            ],
            "인천": [
                {"place_id": "ChIJD_7vNcK4fDUR93DmJ_fIKts", "name": "송도 센트럴파크", "type": "tourist_attraction", 
                 "latitude": 37.3934, "longitude": 126.6340, "rating": 4.5},
                {"place_id": "ChIJ9SOnJmW4fDURtpXSp49sVsQ", "name": "트라이볼", "type": "tourist_attraction", 
                 "latitude": 37.3897, "longitude": 126.6384, "rating": 4.3},
                {"place_id": "ChIJYW6-NcK4fDURHvL0oW7CtJE", "name": "G타워", "type": "tourist_attraction", 
                 "latitude": 37.3938, "longitude": 126.6355, "rating": 4.4},
                {"place_id": "ChIJw1eYEMK4fDURsh74skmIovk", "name": "아트센터인천", "type": "tourist_attraction", 
                 "latitude": 37.3916, "longitude": 126.6358, "rating": 4.5},
                {"place_id": "ChIJvU5wvL-4fDURJU2RF6Z3-G4", "name": "신세계프리미엄아울렛", "type": "shopping_mall", 
                 "latitude": 37.3822, "longitude": 126.6545, "rating": 4.3},
            ],
            "연수구": [
                {"place_id": "ChIJD_7vNcK4fDUR93DmJ_fIKts", "name": "송도 센트럴파크", "type": "tourist_attraction", 
                 "latitude": 37.3934, "longitude": 126.6340, "rating": 4.5},
                {"place_id": "ChIJ9SOnJmW4fDURtpXSp49sVsQ", "name": "트라이볼", "type": "tourist_attraction", 
                 "latitude": 37.3897, "longitude": 126.6384, "rating": 4.3},
                {"place_id": "ChIJYW6-NcK4fDURHvL0oW7CtJE", "name": "G타워", "type": "tourist_attraction", 
                 "latitude": 37.3938, "longitude": 126.6355, "rating": 4.4},
                {"place_id": "ChIJw1eYEMK4fDURsh74skmIovk", "name": "아트센터인천", "type": "tourist_attraction", 
                 "latitude": 37.3916, "longitude": 126.6358, "rating": 4.5},
                {"place_id": "ChIJvU5wvL-4fDURJU2RF6Z3-G4", "name": "신세계프리미엄아울렛", "type": "shopping_mall", 
                 "latitude": 37.3822, "longitude": 126.6545, "rating": 4.3},
            ],
            "default": [
                {"place_id": "ChIJR2xAbGejfDUR74xBkRbpU1k", "name": "명동", "type": "tourist_attraction", 
                 "latitude": 37.5630, "longitude": 126.9839, "rating": 4.3},
                {"place_id": "ChIJBeY2XHGjfDURCjQTGLN3bSk", "name": "덕수궁", "type": "tourist_attraction", 
                 "latitude": 37.5658, "longitude": 126.9748, "rating": 4.5},
                {"place_id": "ChIJLUS2DiKjfDURjvibGi1XT8U", "name": "청계천", "type": "tourist_attraction", 
                 "latitude": 37.5696, "longitude": 127.0026, "rating": 4.4},
                {"place_id": "ChIJt-XSjD6jfDURQUTsAy-_LMI", "name": "동대문디자인플라자(DDP)", "type": "tourist_attraction", 
                 "latitude": 37.5670, "longitude": 127.0089, "rating": 4.4},
                {"place_id": "ChIJXyfpIESifDURJJGjZ1MxRvU", "name": "홍대 거리", "type": "tourist_attraction", 
                 "latitude": 37.5558, "longitude": 126.9237, "rating": 4.3},
            ]
        }
        
        # 지역에 맞는 백업 데이터 선택
        selected_backup = None
        if preferences.region:
            for region_key, places in backup_places.items():
                if region_key in preferences.region:
                    selected_backup = places
                    logger.info(f"Using backup data for region: {region_key}")
                    break
        
        # 매칭되는 지역이 없으면 기본 데이터 사용
        if not selected_backup:
            selected_backup = backup_places["default"]
            logger.info("Using default backup data")
        
        # 백업 데이터 사용
        raw_places = selected_backup
        
        # Geometry 형식 맞추기 - 백업 데이터를 Google Places API 형식으로 변환
        for place in raw_places:
            place["geometry"] = {"location": {"lat": place["latitude"], "lng": place["longitude"]}}
            place["formatted_address"] = f"{preferences.region or '인천'} {place['name']} 근처"
            place["vicinity"] = f"{preferences.region or '인천'}"
            place["types"] = [place["type"]]
    
    # 전체 결과를 한번 더 섞어 랜덤성 강화
    random.shuffle(raw_places)
    
    # 로깅 - 장소 목록 확인
    place_names = [p.get("name", "Unknown") for p in raw_places[:5]]
    logger.info(f"Found places (sample): {', '.join(place_names)}")
    logger.info(f"Total places found: {len(raw_places)}")

    # 2) 스코어링 및 장소 객체 변환
    scored: List[Dict[str, Any]] = []
    seen: set[str] = set()
    
    # 장소 DB 저장 시도 (반복 로직 수정)
    for raw in raw_places:
        pid = raw.get("place_id")
        if not pid or pid in seen:
            continue
            
        place_obj = _convert_google_place_to_schema(raw)
        if not place_obj:
            continue
        
        # DB 캐시: 장소가 DB에 없으면 저장 시도
        existing_place = crud.place.get_by_google_place_id(db, google_place_id=pid)
        if not existing_place:
            try:
                # 장소 생성용 객체 준비 - type 필드 제외
                place_create_data = place_obj.model_dump(mode="python", by_alias=True)
                
                # 'type' 필드를 제거 (DB에 없는 필드)
                if 'type' in place_create_data:
                    del place_create_data['type']
                
                # JSON 형식으로 변환해야 하는 필드 처리
                if 'types' in place_create_data and isinstance(place_create_data['types'], list):
                    place_create_data['types'] = place_create_data['types']  # PostgreSQL은 자동으로 JSON으로 변환

                if 'photo_references' in place_create_data and isinstance(place_create_data['photo_references'], list):
                    place_create_data['photo_references'] = place_create_data['photo_references']
                
                if 'operating_hours' in place_create_data and isinstance(place_create_data['operating_hours'], list):
                    place_create_data['operating_hours'] = place_create_data['operating_hours']
                
                if 'tags' in place_create_data and isinstance(place_create_data['tags'], list):
                    place_create_data['tags'] = place_create_data['tags']
                    
                # create 용 객체 생성
                place_create = schemas.PlaceCreate(**place_create_data)
                
                # DB 저장 시도
                logger.info(f"Saving place to DB: {place_obj.name} ({pid})")
                db_place = crud.place.create(db, obj_in=place_create)
                logger.info(f"Place saved to DB: {pid}")
            except Exception as e:
                logger.error(f"Error saving place {pid} to DB: {e}")
                db.rollback()
        else:
            logger.info(f"Place already exists in DB: {pid}")

        # 더 높은 랜덤성 - 점수에 0.0~0.5 사이 랜덤값 추가
        score = _calculate_score(raw, preferences, origin_lat, origin_lon)
        score += random.random() * 0.5  # 강한 랜덤 요소
        # 장소의 카테고리 타입 저장 (비DB 필드이지만 정렬/필터링용으로 사용)
        place_type = getattr(place_obj, "type", None) or "기타"
        scored.append({"place_obj": place_obj, "score": score, "type": place_type})
        seen.add(pid)

    logger.info(f"Scored places: {len(scored)}")
    
    # 스코어링된 장소가 없으면 에러 중단
    if not scored:
        raise HTTPException(400, "No places could be processed for this route.")

    # 다양성이 보장된 장소 선택 (카테고리 다양성 확보)
    selected_places = _ensure_category_diversity(scored, min_places=5)
    logger.info(f"Selected places after diversity check: {len(selected_places)}")
    
    # 선택된 장소가 너무 적으면 상위 점수 장소로 보충
    if len(selected_places) < 3 and len(scored) > 0:
        # 점수 기준 정렬
        scored.sort(key=lambda x: x["score"], reverse=True)
        # 이미 선택된 장소 ID
        selected_ids = {place["place_obj"].google_place_id for place in selected_places}
        # 추가 장소 선택
        for place in scored:
            if place["place_obj"].google_place_id not in selected_ids and len(selected_places) < 5:
                selected_places.append(place)
                logger.info(f"Added supplementary place: {place['place_obj'].name}")
    
    if len(selected_places) < 3:
        raise HTTPException(400, "Not enough suitable places found.")
    
    # 최종 선택된 장소들을 한번 더 무작위로 섞음
    random.shuffle(selected_places)
    logger.info(f"Final selected places count: {len(selected_places)}")
    
    # 모든 선택된 장소가 DB에 있는지 최종 확인
    for place_data in selected_places:
        place_obj = place_data["place_obj"]
        pid = place_obj.google_place_id
        
        # 최종 확인 - DB에 장소가 있는지 체크
        if not crud.place.get_by_google_place_id(db, google_place_id=pid):
            try:
                # 다시 한번 저장 시도
                place_create_data = place_obj.model_dump(mode="python", by_alias=True)
                place_create = schemas.PlaceCreate(**place_create_data)
                crud.place.create(db, obj_in=place_create)
                logger.info(f"Final check: Place saved to DB: {pid}")
            except Exception as e:
                logger.error(f"Final check: Error saving place {pid} to DB: {e}")
    
    # 최종 경로 이름도 좀 더 다양하게
    style_name = preferences.preferred_styles[0] if preferences.preferred_styles else '추천'
    route_names = [
        f"{style_name} 경로",
        f"{style_name} 여행 코스",
        f"즐거운 {style_name} 투어",
        f"{style_name} 핫플레이스",
        f"맞춤형 {style_name} 코스"
    ]
    route_name = random.choice(route_names)
    
    # 추가: 지역명 포함 (있다면)
    if preferences.region:
        route_name = f"{preferences.region} {route_name}"

    # 이동 정보 생성
    moving_info = await _generate_moving_info(selected_places, preferences)

    # 3) 최종 반환 dict
    # 주의: place 객체 대신 google_place_id만 반환
    result = {
        "name": route_name,
        "description": f"{preferences.budget} 예산, {', '.join(preferences.preferred_styles or [])} 스타일",
        "places": [{"google_place_id": entry["place_obj"].google_place_id} for entry in selected_places],
        "moving_info": moving_info,
        "estimated_duration": "정보 없음",
        "total_distance": "정보 없음",
    }
    
    # 최종 로깅
    logger.info(f"Route generation complete. Places count: {len(result['places'])}")
    logger.info(f"Place IDs: {[p['google_place_id'] for p in result['places']]}")
    
    return result