#!/usr/bin/env python3
"""
데이터베이스에 테스트용 장소 데이터를 직접 추가하는 스크립트
사용법: python add_test_place.py
"""

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

# 백엔드 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import get_db, Base
from app.db.models.place import Place
from app.db.models.review import Review
from app.db.models.user import User

# 데이터베이스 세션 생성
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment variables")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def add_test_place():
    # 기존 테스트 장소 확인 (중복 방지)
    existing_place = db.query(Place).filter(Place.google_place_id == "TEST_PLACE_ID").first()
    if existing_place:
        print(f"테스트 장소가 이미 존재합니다: {existing_place.name}")
        return existing_place

    # 테스트 장소 생성
    test_place = Place(
        google_place_id="TEST_PLACE_ID",
        name="테스트 장소 - 트라이보울",
        address="인천광역시 연수구 송도동 30-1",
        latitude=37.388691,
        longitude=126.639841,
        rating=4.5,
        user_ratings_total=120,
        type="공연장",
        types=["공연장", "문화시설"],
        photo_references=["test_photo_ref"],
        website="https://tribowl.incheon.go.kr/",
        phone_number="032-832-7994",
        description="인천 송도에 위치한 공연장으로, 다양한 문화예술 공연을 선보이는 복합 문화공간입니다."
    )
    
    # 데이터베이스에 저장
    try:
        db.add(test_place)
        db.commit()
        db.refresh(test_place)
        print(f"테스트 장소가 성공적으로 추가되었습니다: {test_place.name}")
        
        # 테스트 리뷰 추가
        add_test_reviews(test_place.google_place_id)
        
        return test_place
    except Exception as e:
        db.rollback()
        print(f"테스트 장소 추가 실패: {e}")
        return None

def add_test_reviews(place_google_id):
    # 테스트 장소 조회
    place = db.query(Place).filter(Place.google_place_id == place_google_id).first()
    if not place:
        print(f"장소를 찾을 수 없습니다: {place_google_id}")
        return
    
    # 테스트 리뷰 데이터
    test_reviews = [
        {
            "author_name": "김철수",
            "rating": 5,
            "text": "아주 좋은 공간이에요! 공연도 훌륭하고 시설도 깨끗합니다. 송도에서 꼭 방문해야 할 곳 중 하나입니다.",
            "relative_time_description": "1달 전"
        },
        {
            "author_name": "이영희",
            "rating": 4,
            "text": "공연이 다양해서 좋아요. 주차 공간이 조금 부족한 것이 아쉽습니다. 대체로 만족스러운 경험이었습니다.",
            "relative_time_description": "2주 전"
        },
        {
            "author_name": "박지성",
            "rating": 5,
            "text": "시설이 깔끔하고 공연 퀄리티도 높았습니다. 송도에서 문화생활을 즐기기 좋은 장소예요.",
            "relative_time_description": "3일 전"
        }
    ]
    
    # 리뷰 추가
    for review_data in test_reviews:
        review = Review(
            place_google_id=place.google_place_id,
            author_name=review_data["author_name"],
            rating=review_data["rating"],
            text=review_data["text"],
            relative_time_description=review_data["relative_time_description"]
        )
        
        try:
            db.add(review)
        except Exception as e:
            db.rollback()
            print(f"리뷰 추가 실패: {e}")
            return

    # 모든 리뷰 커밋
    try:
        db.commit()
        print(f"{len(test_reviews)}개의 테스트 리뷰가 성공적으로 추가되었습니다.")
    except Exception as e:
        db.rollback()
        print(f"리뷰 저장 실패: {e}")

if __name__ == "__main__":
    test_place = add_test_place()
    print("\n테스트 데이터 추가 완료!")
    print(f"프론트엔드에서 다음 ID를 사용하여 테스트하세요: {test_place.google_place_id if test_place else '추가 실패'}")