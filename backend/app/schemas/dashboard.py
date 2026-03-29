from pydantic import BaseModel

class DashboardStats(BaseModel):
    vehicles_in_factory: int
    entries_today: int
    exits_today: int
    pending_review_count: int
    active_alerts_count: int
