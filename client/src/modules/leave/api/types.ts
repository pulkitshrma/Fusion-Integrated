export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export interface LeaveEvent {
  from_status: string;
  to_status: string;
  action: string;
  actor_user_id: number | null;
  note: string;
  created_at: string;
}

export interface LeaveApplication {
  id: number;
  user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: string;
  purpose: string;
  status: string;
  requested_days: string;
  station_leave_required: boolean;
  station_leave_details: Record<string, unknown>;
  substitute_user_id: number | null;
  substitute_response: string;
  current_assignee_user_id: number | null;
  final_decision_by_user_id: number | null;
  final_decision_at: string | null;
  decision_note: string;
  events: LeaveEvent[];
  created_at: string;
  updated_at: string;
}

export interface LeaveBalance {
  category: LeaveCategory;
  year: number;
  employee_kind: "faculty" | "staff";
  credited: string;
  carried_forward: string;
  consumed: string;
  available: string;
}

export interface LeaveLedgerEntry {
  id: number;
  application_id: number | null;
  category: LeaveCategory;
  amount: string;
  entry_type: string;
  reference: string;
  created_at: string;
}

export interface LifecycleRequest {
  id: number;
  application_id: number;
  kind: "cancellation" | "extension" | "resumption";
  status: string;
  requested_start_date: string | null;
  requested_end_date: string | null;
  actual_resumption_date: string | null;
  details: string;
  current_assignee_user_id: number | null;
  final_decision_by_user_id: number | null;
  final_decision_at: string | null;
  decision_note: string;
  events: LeaveEvent[];
  created_at: string;
}

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}
