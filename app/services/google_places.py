# unithon_backend/app/services/google_places.py

import httpx
import logging
# typing 임포트 확인
from typing import Optional, Tuple, List, Dict, Any
from fastapi import HTTPException
# settings 객체를 직접 임포트
from app.core.config import settings
import asyncio
logger = logging.getLogger(__name__)

# --- 여기를 다시 한번 확인해주세요 ---
# settings 객체에서 정확한 이름으로 API 키 가져오기 (GOOGLE_PLACES_API_KEY)
GOOGLE_PLACES_API_KEY = settings.GOOGLE_PLACES_API_KEY
# --- ---

PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"
NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DIRECTIONS_API_URL = "https://maps.googleapis.com/maps/api/directions/json"

async def get_place_details(place_id: str, fields: str = "name,formatted_address,geometry,rating,place_id,types,photo,user_ratings_total,reviews,opening_hours,website,url") -> Optional[Dict[str, Any]]:
    """Fetches details for a specific place."""
    if not GOOGLE_PLACES_API_KEY:
        logger.error("GOOGLE_PLACES_API_KEY is not configured or loaded correctly.")
        return None

    params = {
        "place_id": place_id,
        "fields": fields,
        "key": GOOGLE_PLACES_API_KEY,
        "language": "ko"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(PLACES_DETAILS_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK":
                logger.info(f"Successfully fetched details for place_id: {place_id}")
                return data.get("result")
            else:
                logger.warning(f"Google Places details fetch failed for {place_id}: Status {data.get('status')}, Error: {data.get('error_message')}")
                return None
        except httpx.TimeoutException:
            logger.error(f"Timeout error fetching details for place_id {place_id}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching details for place_id {place_id}: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error fetching details for {place_id}: {e}")
        return None

# ---- backward‑compat alias -------------------------------------------------
async def get_place_details_google(
    place_id: str,
    fields: str = "name,formatted_address,geometry,rating,place_id,types,photo,user_ratings_total,reviews,opening_hours,website,url",
):
    """DEPRECATED – use `get_place_details` instead.  Kept only for existing callers."""
    return await get_place_details(place_id, fields=fields)
# ---------------------------------------------------------------------------


async def get_google_place_photo_direct(
        photo_reference: str,
        max_width: int = 400
) -> tuple[bytes | None, str | None]:
    """
    Fetch raw bytes of a Google Place photo.
    Returns (binary, content_type).  None if fetch fails.
    Google returns *302* first; we must allow redirects.
    """
    url = "https://maps.googleapis.com/maps/api/place/photo"
    params = {
        "photoreference": photo_reference,
        "maxwidth": max_width,
        "key": settings.GOOGLE_PLACES_API_KEY,
    }

    # follow_redirects=True 가 핵심!
    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        headers={
            # 일부 CDN이 UA 없으면 403/302 loop 를 줄 수도 있음
            "User-Agent": "unithon-backend/1.0 (+https://example.com)",
            "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
        },
    ) as client:
        resp = await client.get(url, params=params)
        # 200 OK 가 아닐 때만 예외            ↓ 302 는 더 이상 raise 안 됨
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "image/jpeg")
        return resp.content, content_type

async def get_google_place_photo_by_place_id(place_id: str, max_width: int = 400) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Fetches place details to get a photo reference, then fetches the photo itself.
    Inefficient if details are fetched elsewhere. Prefer using stored photo_reference.
    Returns (photo_content, content_type) or (None, None).
    """
    logger.info(f"Attempting to fetch photo via place_id lookup: {place_id}")
    place_details = await get_place_details(place_id, fields="photo")

    if place_details and "photos" in place_details and place_details["photos"]:
        photo_reference = place_details["photos"][0].get("photo_reference")
        if photo_reference:
            logger.info(f"Found photo_reference for {place_id}, fetching photo directly.")
            return await get_google_place_photo_direct(photo_reference, max_width)
        else:
            logger.warning(f"No photo reference found in details for place_id: {place_id}")
            return None, None
    else:
        logger.warning(f"Could not get photo details for place_id: {place_id}.")
        return None, None

async def search_nearby_places(latitude: float, longitude: float, radius: int, place_type: Optional[str]) -> List[Dict[str, Any]]:
    """Searches for nearby places."""
    if not GOOGLE_PLACES_API_KEY:
        logger.error("GOOGLE_PLACES_API_KEY is not configured or loaded correctly.")
        return []

    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius,
        "key": GOOGLE_PLACES_API_KEY,
        "language": "ko"
    }
    if place_type:
        params["type"] = place_type

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(NEARBY_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK":
                 logger.info(f"Nearby search successful for type '{place_type or 'any'}' near ({latitude},{longitude}). Found {len(data.get('results', []))} places.")
                 return data.get("results", [])
            elif data.get("status") == "ZERO_RESULTS":
                 logger.info(f"Nearby search found zero results for type '{place_type or 'any'}' near ({latitude},{longitude}).")
                 return []
            else:
                logger.warning(f"Google Places nearby search failed: Status {data.get('status')}, Error: {data.get('error_message')}")
                return []
        except httpx.TimeoutException:
            logger.error(f"Timeout error during nearby search near ({latitude},{longitude})")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during nearby search: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error during nearby search: {e}")
            return []
        

async def search_places_google(
    query: str,
    region: Optional[str] = None,
    language: str = "ko",
    limit: int = 60,
) -> List[Dict[str, Any]]:
    """
    Google Places *Text Search* wrapper.

    Parameters
    ----------
    query : str
        Free‑form search terms (e.g. `"인천 송도 카페"`).
    region : str | None
        Optional region bias such as country‑code top‑level domain (`"kr"`).
    language : str
        Response language (default `"ko"`).
    limit : int
        Maximum number of results to return (Google returns ≤20 per page).

    Returns
    -------
    list[dict]
        Raw `results[]` objects from the Places API (may be empty).
    """
    if not GOOGLE_PLACES_API_KEY:
        logger.error("GOOGLE_PLACES_API_KEY is not configured.")
        return []

    params: dict[str, Any] = {
        "query": query,
        "key": GOOGLE_PLACES_API_KEY,
        "language": language,
    }
    if region:
        params["region"] = region

    collected: List[Dict[str, Any]] = []
    next_token: Optional[str] = None

    async with httpx.AsyncClient(timeout=20.0) as client:
        while True:
            if next_token:
                # token must be re‑added for subsequent calls
                params["pagetoken"] = next_token
            try:
                resp = await client.get(TEXT_SEARCH_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.exception("Text search request failed: %s", exc)
                break

            status = data.get("status")
            if status == "OK":
                collected.extend(data.get("results", []))
                if len(collected) >= limit:
                    break
                next_token = data.get("next_page_token")
                if not next_token:
                    break
                # Per Google docs, wait a short time before using next_page_token
                await asyncio.sleep(2.0)
            elif status == "ZERO_RESULTS":
                break
            else:
                logger.warning(
                    "Text search error: status=%s, message=%s",
                    status,
                    data.get("error_message"),
                )
                break

    return collected[:limit]

async def get_directions(
    origin_lat: float,
    origin_lng: float, 
    dest_lat: float,
    dest_lng: float,
    mode: str = "transit",
    language: str = "ko"
) -> Dict[str, Any]:
    """
    Google Directions API를 사용하여 두 지점 간 경로 정보를 가져옴
    
    Parameters
    ----------
    origin_lat : float
        출발지 위도
    origin_lng : float
        출발지 경도
    dest_lat : float
        도착지 위도
    dest_lng : float
        도착지 경도
    mode : str
        이동 수단(driving, walking, bicycling, transit)
    language : str
        언어 설정
        
    Returns
    -------
    Dict[str, Any]
        경로 정보가 담긴 Google Directions API 응답
    """
    if not GOOGLE_PLACES_API_KEY:
        logger.error("GOOGLE_PLACES_API_KEY is not configured.")
        return {}

    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "mode": mode,  # 이동 수단(driving, walking, bicycling, transit)
        "language": language,
        "key": GOOGLE_PLACES_API_KEY,
        "alternatives": "true",  # 대체 경로도 제공
        "region": "kr"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(DIRECTIONS_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "OK":
                logger.info(f"Successfully fetched directions from ({origin_lat},{origin_lng}) to ({dest_lat},{dest_lng})")
                return data
            else:
                logger.warning(f"Google Directions API failed: Status {data.get('status')}, Error: {data.get('error_message')}")
                return {}
        except Exception as e:
            logger.exception(f"Error fetching directions: {e}")
            return {}