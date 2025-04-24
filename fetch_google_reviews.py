#!/usr/bin/env python3
"""
Script to fetch Google reviews for a place and save them to the database.
"""
import asyncio
import sys
from app.db.database import SessionLocal
from app.services.google_places import get_place_details
from app.db.models.review import Review
from app.db.models.place import Place
from app.db import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_and_save_reviews(place_id: str):
    """Fetch reviews for a place and save them to the database."""
    logger.info(f"Fetching details for place: {place_id}")
    # Get details with reviews
    details = await get_place_details(
        place_id,
        fields="name,rating,reviews"
    )
    
    if not details:
        logger.error(f"Could not fetch details for place {place_id}")
        return
    
    logger.info(f"Found place: {details.get('name')}")
    
    # Get Google reviews
    google_reviews = details.get("reviews", [])
    logger.info(f"Found {len(google_reviews)} Google reviews")
    
    if not google_reviews:
        logger.info("No reviews found for this place")
        return
    
    # Save reviews to database
    db = SessionLocal()
    try:
        # Check if place exists
        db_place = db.query(Place).filter(Place.google_place_id == place_id).first()
        if not db_place:
            logger.error(f"Place {place_id} not found in database")
            return
        
        # Log the place details for debugging
        logger.info(f"Found place in DB: {db_place.name} (google_place_id: {db_place.google_place_id})")
        
        system_user_id = "google-reviews-system-user"
        
        for i, review_data in enumerate(google_reviews):
            logger.info(f"Processing review {i+1}/{len(google_reviews)}")
            
            # Check for duplicate reviews - use place_google_id to match the column name in the model
            existing_review = None
            if review_data.get('text'):
                existing_review = (
                    db.query(Review)
                    .filter(
                        Review.place_google_id == db_place.google_place_id,
                        Review.text == review_data.get('text'),
                        Review.author_name == review_data.get('author_name')
                    )
                    .first()
                )
                
            if existing_review:
                logger.info(f"Review already exists, skipping: {review_data.get('author_name')}")
                continue
            
            # Create new review
            new_review = Review(
                owner_id=system_user_id,
                place_google_id=db_place.google_place_id,  # Use the google_place_id from the place model
                rating=review_data.get('rating', 3),
                text=review_data.get('text', ""),
                author_name=review_data.get('author_name', "Google User"),
                profile_photo_url=review_data.get('profile_photo_url'),
                relative_time_description=review_data.get('relative_time_description', "")
            )
            
            try:
                db.add(new_review)
                logger.info(f"Added review by {new_review.author_name}")
            except Exception as e:
                logger.error(f"Error adding review: {e}")
                continue
        
        # Commit all reviews
        db.commit()
        logger.info("All reviews saved successfully")
    except Exception as e:
        logger.error(f"Error processing reviews: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <google_place_id>")
        return
    
    place_id = sys.argv[1]
    asyncio.run(fetch_and_save_reviews(place_id))

if __name__ == "__main__":
    main()
