from .base_class import Base
from .database import engine, SessionLocal, init_db

# 모델들을 import 하여 Base.metadata에 등록되도록 함 (init_db 또는 Alembic에서 사용)
from .models.user import User
from .models.route import DbTravelRoute