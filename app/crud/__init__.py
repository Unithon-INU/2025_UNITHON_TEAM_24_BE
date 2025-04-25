# 아래는 CRUD 네임스페이스 export 용 (기존 그대로 두세요)
from .crud_user import (
    get_user,
    get_user_by_email,
    create_db_user,
    get_or_create_user_firebase,
    authenticate_user,
)

from .crud_route import (
    create_route,
    get_routes_by_owner,
    get_route_by_id,
    update_route,
    delete_route,
    get_without_owner_check,
)

from .crud_place import place
from .crud_review import review
from . import crud_route

class _RouteNamespace:
    create              = staticmethod(create_route)
    get_multi_by_user   = staticmethod(get_routes_by_owner)
    get                 = staticmethod(get_route_by_id)
    update              = staticmethod(update_route)
    remove              = staticmethod(delete_route)
    get_without_owner_check = staticmethod(get_without_owner_check)

# endpoints 에서 `from app.crud import route` 로 가져갈 때 이 네임스페이스를 사용합니다
route = _RouteNamespace()