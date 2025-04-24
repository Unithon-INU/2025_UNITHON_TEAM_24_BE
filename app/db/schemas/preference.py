from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class PreferenceBase(BaseModel):
    region: str
    style: str
    budget: str
    companion: str
    special_request: Optional[str] = Field(None, alias="specialRequest")
    mobility_limit: str = Field(..., alias="mobilityLimit")
    use_public_transport: bool = Field(..., alias="usePublicTransport")

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    preferred_styles: Optional[List[str]] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

class TravelPreferenceCreate(PreferenceBase):
    pass

# Properties to receive via API on creation
class PreferenceCreate(PreferenceBase):
    pass

# Properties to receive via API on update
class PreferenceUpdate(PreferenceBase):
    pass

# Properties stored in DB
class PreferenceInDBBase(PreferenceBase):
    id: Optional[int]       = None
    owner_id: Optional[int] = None

class TravelPreference(PreferenceInDBBase):
    pass

# Additional properties to return via API
class Preference(PreferenceInDBBase):
    pass