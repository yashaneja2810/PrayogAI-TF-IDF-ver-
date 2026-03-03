from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class User(BaseModel):
    id: str
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_sign_in_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda dt: dt.isoformat() if dt else None}
    )
    
    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        # Convert datetime objects to ISO format strings
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d