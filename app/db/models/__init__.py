# DB 모델 클래스들을 쉽게 import 할 수 있도록 함
from .user import User
from .route import DbTravelRoute
# app/db/models/__init__.py
from .place import Place
# 또는, 모델이 route.py 에 있으면
from .review import Review