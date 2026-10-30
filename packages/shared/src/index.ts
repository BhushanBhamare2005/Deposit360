export type User = {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  is_active: boolean;
  institution_id: string | null;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

export type Institution = {
  id: string;
  code: string;
  name: string;
  approval_reference: string | null;
  contact_email: string;
  created_at: string;
};

export type Instrument = {
  id: string;
  institution_id: string;
  instrument_number: string;
  bank_name: string;
  branch_name: string | null;
  holder_name: string;
  amount: number | string;
  issue_date: string;
  maturity_date: string;
  lifecycle_state: "active" | "approaching_maturity" | "matured" | "renewed" | "released";
  created_at: string;
};

export type InstrumentList = {
  items: Instrument[];
  total: number;
};

export type ComplianceCase = {
  id: string;
  instrument_id: string;
  title: string;
  description: string;
  status: "open" | "in_review" | "changes_requested" | "approved" | "rejected";
  resolution_note: string | null;
  created_by: string;
  reviewed_by: string | null;
  created_at: string;
};

export type DashboardSummary = {
  total_instruments: number;
  active_instruments: number;
  approaching_maturity: number;
  total_value: number | string;
  open_cases: number;
};

export type PolicyRule = {
  id: string;
  key: string;
  version: number;
  description: string;
  config: Record<string, unknown>;
  effective_from: string;
  effective_to: string | null;
  created_at: string;
};

export type DocumentRecord = {
  id: string;
  instrument_id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  status: string;
  uploaded_by: string | null;
  created_at: string;
};

export type RenewalLink = {
  id: string;
  previous_instrument_id: string;
  replacement_instrument_id: string;
  status: "confirmed" | "broken";
  created_at: string;
};

export type ReleaseRequest = {
  id: string;
  instrument_id: string;
  requested_by: string;
  reviewed_by: string | null;
  status: "submitted" | "under_review" | "approved" | "rejected";
  justification: string;
  review_note: string | null;
  created_at: string;
};

export type Notification = {
  id: string;
  instrument_id: string | null;
  recipient_user_id: string;
  channel: "in_app" | "email";
  subject: string;
  body: string;
  status: "pending" | "sent" | "failed" | "acknowledged";
  created_at: string;
};

export type VerificationCheck = {
  id: string;
  instrument_id: string;
  check_type: string;
  source: string;
  status: "pending_external" | "confirmed" | "failed" | "unable_to_verify";
  evidence_note: string | null;
  requested_by: string | null;
  reviewed_by: string | null;
  created_at: string;
};

export type AuditEvent = {
  id: string;
  actor_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  created_at: string;
};