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


class AccessDetailRow(BaseModel):
    serial_no: str | None
    event_time: str
    plate_number: str
    direction: str
    checkpoint_name: str
    department_name: str | None
    business_type: str
    document_no: str | None
    source: str
    entered_by_user_name: str | None
    note: str | None


class VehicleDetailRow(BaseModel):
    serial_no: str | None
    plate_number: str
    vehicle_type: str
    company: str | None
    contact_name: str | None
    contact_phone: str | None
    status: str
    last_seen_at: str | None
    note: str | None


class UserDetailRow(BaseModel):
    serial_no: str | None
    name: str
    phone: str
    role: str
    factory_name: str | None
    department_name: str | None
    is_active: bool
    created_at: str
