from datetime import datetime
from pydantic import BaseModel

class DashboardStats(BaseModel):
    vehicles_in_factory: int
    entries_today: int
    exits_today: int
    pending_review_count: int
    active_alerts_count: int


class DashboardRecentAccessNode(BaseModel):
    checkpoint_id: str
    checkpoint_name: str
    event_time: datetime


class DashboardRecentAccessRecord(BaseModel):
    record_no: str
    plate_number: str
    entry_time: datetime | None
    exit_time: datetime | None
    stay_duration_minutes: int | None
    status: str
    path_nodes: list[DashboardRecentAccessNode]
