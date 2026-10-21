const ROOT = "/api/backend/borrower/v1";

function csrf(): string {
  if (typeof document === "undefined") return "";
  return decodeURIComponent(document.cookie.split("; ").find((item) => item.startsWith("pg_borrower_csrf="))?.split("=")[1] ?? "");
}

export async function borrowerFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (init.method && init.method !== "GET") headers.set("X-Borrower-CSRF", csrf());
  const response = await fetch(`${ROOT}${path}`, { ...init, headers, credentials: "same-origin", cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: string | Array<{ msg?: string }> };
    const detail = Array.isArray(payload.detail) ? payload.detail.map((item) => item.msg).join("; ") : payload.detail;
    throw Object.assign(new Error(detail || `Permintaan gagal (${response.status})`), { status: response.status });
  }
  return response.json() as Promise<T>;
}

export type EstimateStage = { type: "stage"; stage: string; message: string };
type EstimateEvent = EstimateStage | { type: "complete"; estimate: Estimate } | { type: "error"; message: string };

export async function borrowerEstimateStream(
  body: FormData,
  onStage: (event: EstimateStage) => void,
  signal?: AbortSignal,
): Promise<Estimate> {
  const response = await fetch(`${ROOT}/estimates/stream`, {
    method: "POST", body, signal, credentials: "same-origin", cache: "no-store",
    headers: { "X-Borrower-CSRF": csrf() },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: string | Array<{ msg?: string }> };
    const detail = Array.isArray(payload.detail) ? payload.detail.map((item) => item.msg).join("; ") : payload.detail;
    throw new Error(detail || `Permintaan gagal (${response.status})`);
  }
  if (!response.body) throw new Error("Sambungan progres analisis tidak tersedia.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let estimate: Estimate | null = null;
  const handleLine = (line: string) => {
    if (!line.trim()) return;
    const event = JSON.parse(line) as EstimateEvent;
    if (event.type === "stage") onStage(event);
    if (event.type === "error") throw new Error(event.message);
    if (event.type === "complete") estimate = event.estimate;
  };
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) handleLine(line);
      if (done) break;
    }
    handleLine(buffer);
  } finally {
    reader.releaseLock();
  }
  if (!estimate) throw new Error("Analisis berhenti sebelum hasil selesai. Silakan coba lagi.");
  return estimate;
}

export type BorrowerMe = { id: string; full_name: string; email: string; phone_masked: string; partner: { name: string; slug: string } };
export type BorrowerKyc = {
  id: string | null; status: string; can_apply: boolean; national_id_masked: string | null;
  legal_name: string | null; verification_method: string | null; decision_reason: string | null;
  created_at: string | null; expires_at: string | null;
};
export type BorrowerKtpOcrPreview = {
  fields: { nik: string; legal_name: string; birth_place: string; birth_date: string; gender: string;
    address: string; province: string; city: string; occupation: string; confidence: number | null };
  message: string;
};
export type BorrowerConfig = {
  partner: { name: string };
  branches: Array<{ id: string; code: string; name: string; city: string }>;
  products: Array<{ id: string; name: string; min_amount: number; max_amount: number; allowed_tenors_days: number[]; max_ltv_percent: number; service_fee_percent: number }>;
  categories: Array<{ code: string; name: string }>;
  consent_version: string;
};
export type Estimate = {
  id: string; status: "SUCCESS" | "NEEDS_REVIEW" | "UNSUPPORTED";
  asset_description: string | null;
  quality_score: number; quality_findings: string[]; vision_status: string;
  vision_result: Record<string, unknown>; low_value: number | null; high_value: number | null;
  research_result: { status?: string; searched_at?: string; reason?: string; queries?: string[]; selected?: Array<{ title: string; url: string; host: string; price_idr: number; price_kind: string; source_date?: string; price_evidence?: string }> };
  confidence: number | null; comparable_count: number; explanation: string;
  model_name: string; estimator_version: string; created_at: string;
};
export type BorrowerApplication = { id: string; application_no: string; status: string; requested_amount: number; requested_tenor_days: number; created_at: string };
export type BorrowerDetail = BorrowerApplication & {
  purpose: string | null; kyc_status: string; asset: { category: string; brand: string | null; model: string | null; condition_grade: string } | null;
  estimate: Estimate | null;
  appraisal: { market_value: number; liquidation_value: number; recommended_loan: number; rationale: string; status: string } | null;
  offer: { id: string; principal_amount: number; tenor_days: number; service_fee_amount: number; total_due_amount: number; decision_reason: string | null; agreement_version: string; expires_at: string; status: string } | null;
  history: Array<{ status: string; note: string | null; at: string }>;
};
export type AgreementDocument = {
  schema: string; document_number: string; document_version: string; offer_version: number;
  application_number: string; issued_at: string; expires_at: string;
  company: { name: string; branch: string; branch_address: string; branch_city: string };
  borrower: { name: string; customer_reference: string };
  collateral: { asset_code: string; category: string; brand: string; model: string; condition_grade: string };
  valuation: { market_value_idr: string; liquidation_value_idr: string };
  terms: {
    principal_idr: string; tenor_days: number; service_fee_idr: string; total_due_idr: string;
    requested_principal_idr: string; requested_tenor_days: number | null; decision_reason: string;
    tenor_start: string; disbursement: string; late_fee: string; default_and_collateral: string; dispute: string;
  };
  notice: string;
};
export type AgreementPreview = { document: AgreementDocument; preview_sha256: string };
export type AgreementRecord = {
  id: string; sbg_number: string; document_version: string; status: string; accepted_at: string;
  document_digest: string | null; consent_digest: string | null; chain_status: string;
  chain_id: number; contract_address: string | null; tx_hash: string | null; block_number: number | null;
  confirmed_at: string | null; explorer_url: string | null;
  document_salt?: string | null; opaque_chain_id?: string | null;
  document?: AgreementDocument | null;
  consent?: { accepted_at: string; channel: string; signature_level: string } | null;
};
export type AgreementVerification = AgreementRecord & { local_integrity: boolean; chain_match: boolean; detail: string | null };
export const money = (value: number | string | null | undefined) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value ?? 0));
