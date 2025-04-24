# unithon_backend/app/crud/crud_review.py

from typing import List

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.db import models # models 임포트 수정
from app.db import schemas # schemas 임포트 수정


class CRUDReview(CRUDBase[models.Review, schemas.ReviewCreate, schemas.ReviewUpdate]):
    def create_with_user_and_place(
        self, db: Session, *, obj_in: schemas.ReviewCreate, user_id: int, place_google_id: str
    ) -> models.Review:
        """Creates a new review and associates it with a user and a place.
        (This is likely for reviews created directly within the app by logged-in users)"""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data, user_id=user_id, place_google_id=place_google_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_with_place(
        self, db: Session, *, obj_in: schemas.ReviewCreate, place_google_id: str
    ) -> models.Review:
        """Creates a new review and associates it with a place.
        (Handles cases like Google reviews where there's no internal user_id)"""
        obj_in_data = obj_in.dict()
        
        # Check for duplicate reviews to avoid inserting the same Google review multiple times
        existing_review = None
        if obj_in_data.get('text'):
            existing_review = (
                db.query(self.model)
                .filter(
                    models.Review.place_google_id == place_google_id,
                    models.Review.text == obj_in_data.get('text'),
                    models.Review.author_name == obj_in_data.get('author_name')
                )
                .first()
            )
            
        if existing_review:
            return existing_review
        
        # For Google reviews, use a special system user ID as owner_id
        # This is a workaround since our schema requires a non-null owner_id
        system_user_id = "google-reviews-system-user"
        
        # Create the review with the special system user ID
        db_obj = self.model(
            **obj_in_data,
            owner_id=system_user_id,
            place_google_id=place_google_id
        )
        
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception as e:
            db.rollback()
            import logging
            logging.error(f"Failed to create review: {e}")
            # If the main issue is with owner_id being non-null, add logging
            raise

    def get_multi_by_place(
        self, db: Session, *, place_id: str, skip: int = 0, limit: int = 100
    ) -> List[models.Review]:
        """Retrieve reviews for a specific place."""
        return (
            db.query(self.model)
            .filter(models.Review.place_google_id == place_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_multi_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.Review]:
        """Retrieve reviews created by a specific user."""
        return (
            db.query(self.model)
            .filter(models.Review.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )


review = CRUDReview(models.Review)