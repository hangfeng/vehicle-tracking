export type UserRole = "group_admin" | "factory_manager" | "operator";

export interface User {
  id: string;
  name: string;
  phone: string;
  role: UserRole;
  factory_id: string | null;
}

export type Direction = "entry" | "exit";
export type ReviewStatus = "auto_confirmed" | "pending_review" | "manually_confirmed" | "rejected";
export type VehicleStatus = "in_factory" | "out" | "unknown";
export type AlertType = "long_stay" | "pending_review";
export type AlertStatus = "active" | "resolved";

export interface GateEvent {
  id: string;
  factory_id: string;
  plate_number: string;
  direction: Direction;
  captured_at: string;
  image_url: string | null;
  confidence_score: number | null;
  review_status: ReviewStatus;
  is_manual: boolean;
}

export interface Vehicle {
  id: string;
  factory_id: string;
  plate_number: string;
  vehicle_type: string;
  company: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  status: VehicleStatus;
  last_seen_at: string | null;
  note: string | null;
}

export interface Alert {
  id: string;
  factory_id: string;
  vehicle_id: string | null;
  type: AlertType;
  message: string;
  severity: string;
  status: AlertStatus;
  created_at: string;
  resolved_at: string | null;
  note: string | null;
}

export interface DashboardStats {
  vehicles_in_factory: number;
  entries_today: number;
  exits_today: number;
  pending_review_count: number;
  active_alerts_count: number;
}
