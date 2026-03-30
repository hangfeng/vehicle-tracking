export type UserRole = "group_admin" | "factory_manager" | "operator";

export interface User {
  id: string;
  name: string;
  phone: string;
  role: UserRole;
  factory_id: string | null;
  is_active: boolean;
  created_at: string;
}

export type Direction = "entry" | "exit";
export type ReviewStatus = "auto_confirmed" | "pending_review" | "manually_confirmed" | "rejected";
export type VehicleStatus = "in_factory" | "out" | "unknown";
export type AlertType = "long_stay" | "pending_review" | "path_deviation";
export type AlertStatus = "active" | "resolved";
export type IdentificationMethod = "camera" | "manual";
export type JourneyStatus = "active" | "completed" | "deviated";
export type JourneyDirection = "entry" | "exit";

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
  current_checkpoint_id: string | null;
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

export interface CheckPoint {
  id: string;
  factory_id: string;
  name: string;
  identification_method: IdentificationMethod;
  is_gate: boolean;
  camera_config: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
}

export interface PathTemplateStep {
  id: string;
  checkpoint_id: string;
  step_order: number;
  direction: "entry" | "exit" | "any";
}

export interface PathTemplate {
  id: string;
  factory_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  steps: PathTemplateStep[];
}

export interface VehicleJourney {
  id: string;
  vehicle_id: string;
  factory_id: string;
  template_id: string | null;
  started_at: string;
  completed_at: string | null;
  status: JourneyStatus;
}

export interface DailyTraffic {
  date: string;
  entries: number;
  exits: number;
}

export interface TrafficReport {
  total_entries: number;
  total_exits: number;
  avg_stay_duration_minutes: number | null;
  by_day: DailyTraffic[];
  by_checkpoint: Array<{ checkpoint_id: string; name: string; entries: number; exits: number }>;
}

export interface AlertReport {
  total_active: number;
  total_resolved: number;
  by_type: Array<{ type: string; count: number }>;
}
