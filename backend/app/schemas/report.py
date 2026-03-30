from pydantic import BaseModel

class DailyTraffic(BaseModel):
    date: str
    entries: int
    exits: int

class CheckpointTraffic(BaseModel):
    checkpoint_id: str
    name: str
    entries: int
    exits: int

class TrafficReport(BaseModel):
    total_entries: int
    total_exits: int
    avg_stay_duration_minutes: float | None
    by_day: list[DailyTraffic]
    by_checkpoint: list[CheckpointTraffic]

class VehicleActivity(BaseModel):
    vehicle_id: str
    plate_number: str
    total_visits: int
    alert_count: int

class VehicleReport(BaseModel):
    vehicles: list[VehicleActivity]

class AlertSummaryItem(BaseModel):
    type: str
    count: int

class AlertReport(BaseModel):
    total_active: int
    total_resolved: int
    by_type: list[AlertSummaryItem]
