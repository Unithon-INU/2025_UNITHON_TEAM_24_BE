# app/db/schemas/__init__.py

from .place import (
    Place,
    PlaceBase,
    PlaceCreate,
    PlaceUpdate,
)
from .review import Review, ReviewCreate, ReviewUpdate
from .route import (
    PlaceRef,
    TravelRouteBase,
    TravelRouteCreate,
    TravelRouteUpdate,
    TravelRoute,
)
from .preference import TravelPreference, TravelPreferenceCreate

from .user import (
    UserBase,
    UserCreateSignup,
    UserCreate,
    UserUpdate,
    UserInDBBase,
    User,
    UserInDB,
)

from .token import (
    Token,
    TokenPayload,
)
from .error import HTTPError