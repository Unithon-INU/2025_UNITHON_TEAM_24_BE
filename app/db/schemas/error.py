# app/db/schemas/error.py
from pydantic import BaseModel

class HTTPError(BaseModel):
    detail: str

    class Config:
        # pydantic v2: orm_mode → from_attributes 로 변경
        from_attributes = True