# app/crud/crud_place.py

from typing import Optional
from sqlalchemy.orm import Session

from app.db import models, schemas
from app.crud.base import CRUDBase

class CRUDPlace(
    CRUDBase[models.Place, schemas.PlaceCreate, schemas.PlaceUpdate]
):
    def get_by_google_place_id(
        self,
        db: Session,
        google_place_id: str
    ) -> Optional[models.Place]:
        """
        Return a Place record matching the given Google Place ID, or None.
        """
        return (
            db.query(self.model)
              .filter(self.model.google_place_id == google_place_id)
              .first()
        )

# expose a singleton
place = CRUDPlace(models.Place)