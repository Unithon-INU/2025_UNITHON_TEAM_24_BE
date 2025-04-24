# unithon_backend/app/db/schemas/common.py (수정 불필요 예상)
from pydantic import BaseModel, ConfigDict

class BaseModelWithConfig(BaseModel):
    """
    공통 Pydantic V2 설정을 포함하는 기본 모델.
    - from_attributes=True: ORM 객체로부터 모델 인스턴스 생성 허용 (orm_mode 대체)
    - populate_by_name=True: 필드 별칭(alias)으로 데이터 채우기 허용 (allow_population_by_field_name 대체)
    """
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )