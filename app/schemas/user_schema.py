from pydantic import BaseModel
from datetime import datetime

class UserTokenSchema(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str
    created_at: datetime
