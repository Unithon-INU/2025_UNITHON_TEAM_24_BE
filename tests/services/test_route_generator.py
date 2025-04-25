# tests/services/test_route_generator.py
import pytest
from app.services.route_generator import _convert_google_place_to_schema
from app.db import schemas # schemas.Place 사용 위해 import

def test_convert_google_place_to_schema_valid():
    """유효한 Google API 응답 데이터 변환 테스트"""
    place_data = {
        "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
        "name": "Google Sydney",
        "formatted_address": "1 Darling Island Rd, Pyrmont NSW 2009, Australia",
        "geometry": {"location": {"lat": -33.8666, "lng": 151.1958}},
        "types": ["establishment", "point_of_interest"],
        "rating": 4.5,
        "photos": [{"photo_reference": "AZose0lj7..."}] # 실제 photo_reference 필요 없음
        # opening_hours 등 다른 필드 추가 가능
    }
    # settings.GOOGLE_PLACES_API_KEY가 설정되어 있다고 가정 (테스트 환경 설정 필요)
    # 여기서는 image_url 생성 부분은 제외하고 테스트하거나 mocking 필요

    place_schema = _convert_google_place_to_schema(place_data)

    assert place_schema is not None
    assert isinstance(place_schema, schemas.Place)
    assert place_schema.id == "ChIJN1t_tDeuEmsRUsoyG83frY4"
    assert place_schema.name == "Google Sydney"
    assert place_schema.rating == 4.5
    assert place_schema.latitude == -33.8666
    assert place_schema.longitude == 151.1958
    assert "establishment" in place_schema.tags

def test_convert_google_place_to_schema_missing_location():
    """위치 정보 누락 시 None 반환 테스트"""
    place_data = {
        "place_id": "some_id",
        "name": "No Location Place",
        "types": ["cafe"]
        # geometry 누락
    }
    assert _convert_google_place_to_schema(place_data) is None

# TODO: 더 많은 테스트 케이스 추가 (필수 필드 누락, 타입 오류 등)