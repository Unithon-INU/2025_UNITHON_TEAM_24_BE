#!/usr/bin/env python3
"""
Google Places API 테스트 스크립트
사용법: python test_place_api.py <place_id>
"""

import sys
import asyncio
import json
from dotenv import load_dotenv
import os
import aiohttp

# .env 파일 로드
load_dotenv()
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

if not API_KEY:
    print("Error: GOOGLE_PLACES_API_KEY not found in .env file")
    sys.exit(1)

async def test_place_details(place_id: str):
    """지정된 장소 ID에 대한 상세 정보를 가져옵니다."""
    print(f"Testing Place Details API for place_id: {place_id}")
    print(f"Using API key: {API_KEY[:5]}...{API_KEY[-4:]}")
    
    fields = "name,formatted_address,geometry,rating,reviews"
    url = f"https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": fields,
        "key": API_KEY,
        "language": "ko"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            result = await response.json()
            
            print("\n=== API Response ===")
            print(f"Status: {result.get('status')}")
            
            if result.get('status') != 'OK':
                print(f"Error: {result.get('error_message', 'Unknown error')}")
                return
            
            # 기본 장소 정보 출력
            place = result.get('result', {})
            print("\n=== Place Details ===")
            print(f"Name: {place.get('name')}")
            print(f"Address: {place.get('formatted_address')}")
            print(f"Rating: {place.get('rating')}")
            
            # 리뷰 정보 출력 
            reviews = place.get('reviews', [])
            print(f"\n=== Reviews ({len(reviews)}) ===")
            for i, review in enumerate(reviews[:3], 1):  # 최대 3개만 출력
                print(f"\nReview {i}:")
                print(f"  Author: {review.get('author_name')}")
                print(f"  Rating: {review.get('rating')}")
                print(f"  Text: {review.get('text')[:100]}...")  # 괄호 수정

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <place_id>")
        sys.exit(1)
        
    place_id = sys.argv[1]
    asyncio.run(test_place_details(place_id))