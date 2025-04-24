from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    # JWT의 'sub' 클레임에 저장될 사용자 ID
    sub: Optional[str] = None