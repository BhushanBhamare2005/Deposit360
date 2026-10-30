import type {
  AuthResponse,
  AuditEvent,
  ComplianceCase,
  DashboardSummary,
  DocumentRecord,
  Institution,
  Instrument,
  InstrumentList,
  Notification,
  PolicyRule,
  ReleaseRequest,
  RenewalLink,
  User,
  VerificationCheck
} from "@deposit360/shared";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production" ? "/api/v1" : "http://localhost:8000/api/v1")
).replace(/\/$/, "");
export const MAX_UPLOAD_SIZE_MB = Number(
  process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB || (process.env.NODE_ENV === "production" ? 4 : 20)
);

type RequestOptions = Omit<RequestInit, "headers"> & {
  token?: string;
  headers?: HeadersInit;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.token) headers.set("Authorization", "Bearer " + options.token);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    cache: "no-store"
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string | { message?: string } }
      | null;
    const detail = body?.detail;
    const message =
      typeof detail === "string" ? detail : detail?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function downloadDocument(
  token: string,
  instrumentId: string,
  documentId: string
): Promise<Blob> {
  const response = await fetch(
    `${API_URL}/instruments/${instrumentId}/documents/${documentId}/download`,
    {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store"
    }
  );
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail || `Document download failed (${response.status})`);
  }
  return response.blob();
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    }),
  register: (email: string, full_name: string, password: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, full_name, password })
    }),
  me: (token: string) => request<User>("/users/me", { token }),
  createInstitution: (
    token: string,
    input: Pick<Institution, "code" | "name" | "contact_email"> &
      Partial<Pick<Institution, "approval_reference">>
  ) =>
    request<Institution>("/institutions", {
      method: "POST",
      token,
      body: JSON.stringify(input)
    }),
  getInstitution: (token: string) => request<Institution>("/institutions/me", { token }),
  instruments: (token: string) => request<InstrumentList>("/instruments", { token }),
  instrument: (token: string, instrumentId: string) =>
    request<Instrument>(`/instruments/${instrumentId}`, { token }),
  documents: (token: string, instrumentId: string) =>
    request<DocumentRecord[]>(`/instruments/${instrumentId}/documents`, { token }),
  downloadDocument,
  summary: (token: string) => request<DashboardSummary>("/dashboard/summary", { token }),
  cases: (token: string) => request<ComplianceCase[]>("/cases", { token }),
  case: (token: string, caseId: string) =>
    request<ComplianceCase>(`/cases/${caseId}`, { token }),
  createInstrument: (
    token: string,
    input: Pick<
      Instrument,
      | "instrument_number"
      | "bank_name"
      | "branch_name"
      | "holder_name"
      | "amount"
      | "issue_date"
      | "maturity_date"
    >
  ) =>
    request<Instrument>("/instruments", {
      method: "POST",
      token,
      body: JSON.stringify(input)
    }),
  createCase: (token: string, instrumentId: string, title: string, description: string) =>
    request<ComplianceCase>(`/cases/instruments/${instrumentId}`, {
      method: "POST",
      token,
      body: JSON.stringify({ title, description })
    }),
  uploadDocument: (token: string, instrumentId: string, file: File) => {
    if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
      throw new Error(`PDFs must be ${MAX_UPLOAD_SIZE_MB} MB or smaller.`);
    }
    const body = new FormData();
    body.append("file", file);
    return request<DocumentRecord>(`/instruments/${instrumentId}/documents`, {
      method: "POST",
      token,
      body
    });
  },
  audit: (token: string) => request<AuditEvent[]>("/audit?limit=100", { token }),
  auditEvent: (token: string, eventId: string) =>
    request<AuditEvent>(`/audit/${eventId}`, { token }),
  renewals: (token: string) => request<RenewalLink[]>("/renewals", { token }),
  createRenewal: (
    token: string,
    previous_instrument_id: string,
    replacement_instrument_id: string
  ) =>
    request<RenewalLink>("/renewals", {
      method: "POST",
      token,
      body: JSON.stringify({ previous_instrument_id, replacement_instrument_id })
    }),
  releases: (token: string) => request<ReleaseRequest[]>("/releases", { token }),
  release: (token: string, requestId: string) =>
    request<ReleaseRequest>(`/releases/${requestId}`, { token }),
  createRelease: (token: string, instrumentId: string, justification: string) =>
    request<ReleaseRequest>(`/releases/instruments/${instrumentId}`, {
      method: "POST",
      token,
      body: JSON.stringify({ justification })
    }),
  reviewRelease: (
    token: string,
    requestId: string,
    status: ReleaseRequest["status"],
    review_note: string
  ) =>
    request<ReleaseRequest>(`/releases/${requestId}`, {
      method: "PATCH",
      token,
      body: JSON.stringify({ status, review_note })
    }),
  notifications: (token: string) => request<Notification[]>("/notifications", { token }),
  acknowledgeNotification: (token: string, notificationId: string) =>
    request<Notification>(`/notifications/${notificationId}/acknowledge`, {
      method: "PATCH",
      token
    }),
  verifyInstrument: (token: string, instrumentId: string) =>
    request<VerificationCheck>(`/verification/instruments/${instrumentId}`, {
      method: "POST",
      token
    }),
  verifications: (token: string, instrumentId: string) =>
    request<VerificationCheck[]>(`/verification/instruments/${instrumentId}`, { token }),
  reviewVerification: (
    token: string,
    checkId: string,
    status: VerificationCheck["status"],
    evidence_note: string
  ) =>
    request<VerificationCheck>(`/verification/${checkId}`, {
      method: "PATCH",
      token,
      body: JSON.stringify({ status, evidence_note })
    }),
  reviewCase: (
    token: string,
    caseId: string,
    status: ComplianceCase["status"],
    resolution_note: string
  ) =>
    request<ComplianceCase>(`/cases/${caseId}`, {
      method: "PATCH",
      token,
      body: JSON.stringify({ status, resolution_note })
    }),
  resubmitCase: (token: string, caseId: string) =>
    request<ComplianceCase>(`/cases/${caseId}/resubmit`, { method: "POST", token }),
  policyRules: (token: string) => request<PolicyRule[]>("/policy-rules", { token }),
  createPolicyRule: (
    token: string,
    input: Pick<PolicyRule, "key" | "description" | "config" | "effective_from" | "effective_to">
  ) =>
    request<PolicyRule>("/policy-rules", {
      method: "POST",
      token,
      body: JSON.stringify(input)
    }),
  extractDocument: (token: string, documentId: string) =>
    request<{
      document_id: string;
      text: string;
      fields: {
        id: string;
        field_name: string;
        extracted_value: string;
        page_number: number | null;
        confidence: number | null;
      }[];
      ocr_used: boolean;
    }>(`/documents/${documentId}/extract`, { method: "POST", token })
};