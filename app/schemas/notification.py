from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    message: str
    type: str = "info"  # 'info', 'appointment', 'stock', 'alert'
    is_read: bool = False
    link: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListOut(BaseModel):
    items: List[NotificationOut]
    total: int
    unread_count: int


class NotificationCreateIn(BaseModel):
    title: str
    message: str
    type: str = "info"
    link: Optional[str] = None


class NotificationMarkReadIn(BaseModel):
    is_read: bool = True
