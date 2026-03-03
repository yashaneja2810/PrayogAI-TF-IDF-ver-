from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class Bot(BaseModel):
    id: str
    bot_id: str
    user_id: str
    name: str
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda dt: dt.isoformat() if dt else None}
    )
    
    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d