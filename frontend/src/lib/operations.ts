import { apiDownload, apiFetch, apiUpload } from "@/lib/api";

export type BranchSummary = {
  id: string;
  code: string;
  name: string;
  city: string;
  is_active: boolean;
};

export type OperationsMetrics = {
  submitted: number;
  under_review: number;
  appraisal: number;
  offered: number;
  accepted: number;
  exceptions: number;
  requested_amount: number;
};

export type ApplicationQueueItem = {
  id: string;
  application_no: string;
  borrower_name: string;
  phone_masked: string;
  branch_name: string;
  branch_code: string;
  status: string;
  priority: string;
  asset_category: string;
  asset_label: string;
  requested_amount: number;
  indicative_value: number | null;
  collateral_status: string;
  submitted_at: string | null;
};

export type CollateralStatusItem = {
  status: string;
  count: number;
};

export type ActivityItem = {
  id: string;
  application_id: string;
  application_no: string;
  to_status: string;
  note: string | null;
  created_at: string;
};

export type OperationsDashboard = {
  generated_at: string;
  branches: BranchSummary[];
  metrics: OperationsMetrics;
  work_queue: ApplicationQueueItem[];
  collateral: CollateralStatusItem[];
  recent_activity: ActivityItem[];
};

export const getOperationsDashboard = () =>
  apiFetch<OperationsDashboard>("/v1/operations/dashboard");

export const listApplications = (limit = 50) =>
  apiFetch<ApplicationQueueItem[]>(`/v1/applications?limit=${limit}`);

export type MasterItem = {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
};

export type BranchItem = MasterItem & { city: string; address: string | null };
export type AssetCategoryItem = MasterItem & {
  description: string | null;
  requires_serial_number: boolean;
};
export type LoanProductItem = MasterItem & {
  agreement_type: string;
  min_amount: number;
  max_amount: number;
  max_ltv_percent: number;
  allowed_tenors_days: number[];
  service_fee_percent: number;
  fee_rules: Record<string, unknown>;
  approval_policy: Record<string, unknown>;
};
export type StaffAssignmentItem = {
  id: string;
  user_id: string;
  user_name: string;
  branch_id: string;
  branch_name: string;
  operational_role: string;
  is_active: boolean;
};

export type ApplicationDetail = {
  id: string;
  application_no: string;
  status: string;
  priority: string;
  branch: Record<string, string>;
  product: Record<string, string> | null;
  borrower: Record<string, string>;
  asset: Record<string, string | number | null>;
  requested_amount: number;
  requested_tenor_days: number | null;
  purpose: string | null;
  submitted_at: string | null;
  evidence: Array<Record<string, unknown>>;
  appraisals: Array<Record<string, unknown>>;
  offers: Array<Record<string, unknown>>;
  pickup: Record<string, unknown> | null;
  loan: Record<string, unknown> | null;
  incidents: Array<Record<string, unknown>>;
  history: Array<Record<string, unknown>>;
};

export type EvidenceItem = {
  id: string;
  application_id: string;
  subject_type: "application" | "appraisal" | "custody_movement" | "incident";
  subject_id: string;
  evidence_type: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  scan_status: string;
  scanner_engine: string | null;
  scan_detail: string | null;
  scanned_at: string | null;
  created_at: string;
};

export type CollateralTimeline = {
  application_id: string;
  application_no: string;
  asset_code: string;
  collateral_status: string;
  events: Array<Record<string, unknown>>;
};

export type ActionResult = {
  id: string;
  application_id: string;
  status: string;
  message: string;
};

export type PublicIntakeConfig = {
  partner: { id: string; slug: string; name: string };
  branches: BranchItem[];
  asset_categories: AssetCategoryItem[];
  loan_products: LoanProductItem[];
  consent_version: string;
};

export type FieldTaskItem = {
  id: string;
  application_id: string;
  application_no: string;
  assignment_code: string;
  status: string;
  scheduled_at: string | null;
  pickup_address: string;
  borrower_name: string;
  phone_masked: string;
  asset_label: string;
  branch_name: string;
};

export type FinanceOverview = {
  cash_balance: number;
  active_loan_count: number;
  outstanding_principal: number;
  outstanding_fee: number;
  payment_today: number;
  open_teller_sessions: number;
  recent_transactions: Array<Record<string, unknown>>;
};

export type FinancialReports = {
  trial_balance: Array<Record<string, unknown>>;
  loan_portfolio: Record<string, unknown>;
  aging: Array<Record<string, unknown>>;
  branch_analytics: Array<Record<string, unknown>>;
};

export type CustomerListItem = {
  id: string;
  customer_reference: string;
  full_name: string;
  phone_masked: string;
  dati_ii_code: string | null;
  slik_subject_code: string | null;
  risk_status: string;
  internal_watchlist: boolean;
  correction_status: string;
};

export type CustomerDetail = {
  id: string;
  customer_reference: string;
  full_name: string;
  phone_masked: string;
  created_at: string;
  profile: {
    national_id_masked: string | null;
    dati_ii_code: string | null;
    slik_subject_code: string | null;
    risk_status: string;
    risk_notes: string | null;
    internal_watchlist: boolean;
    watchlist_reason: string | null;
    correction_status: string;
  };
  summary: {
    application_count: number;
    active_loan_count: number;
    collateral_count: number;
    total_outstanding: number;
    open_collection_count: number;
    open_complaint_count: number;
  };
  applications: Array<{
    id: string;
    application_no: string;
    status: string;
    priority: string;
    branch_code: string;
    branch_name: string;
    requested_amount: number;
    submitted_at: string | null;
    asset: null | {
      id: string;
      asset_code: string;
      category: string;
      label: string;
      collateral_status: string;
      indicative_value: number | null;
    };
    loan: null | {
      id: string;
      account_no: string;
      status: string;
      principal_amount: number;
      outstanding_principal: number;
      outstanding_fee: number;
      paid_amount: number;
      due_at: string | null;
    };
  }>;
  consents: Array<Record<string, unknown>>;
  collections: Array<Record<string, unknown>>;
  complaints: Array<Record<string, unknown>>;
  activity: Array<Record<string, unknown>>;
};

export type DomainEvent = {
  id: string;
  event_type: string;
  category: "loan" | "collateral" | "finance" | "regulatory" | string;
  title: string;
  description: string;
  aggregate_type: string;
  aggregate_id: string;
  aggregate_reference: string;
  actor_id: string | null;
  occurred_at: string;
  metadata: Record<string, unknown>;
};

export type KycVerification = {
  id: string; status: string; document_type: string; national_id_masked: string; legal_name: string;
  birth_place: string; birth_date: string; gender: string; address: string; province: string; city: string;
  occupation: string | null; verification_method: string; provider_name: string | null; provider_reference: string | null;
  risk_level: string; face_match_score: number | null; liveness_score: number | null;
  document_authenticity_score: number | null; pep_match: boolean; sanctions_match: boolean;
  decision_reason: string | null; initiated_by_user_id: string; reviewed_by_user_id: string | null;
  created_at: string; reviewed_at: string | null; expires_at: string | null;
  documents: Array<Record<string, unknown>>; events: Array<Record<string, unknown>>;
  provider_checks: KycProviderCheck[];
};

export type KycProviderCheck = {
  id: string; check_type: "ocr" | "identity_verification"; provider_name: string;
  environment: "local" | "sandbox" | "live" | "provider"; status: string;
  provider_reference: string | null; officially_verified: boolean;
  result: Record<string, unknown>; requested_by_user_id: string; completed_at: string;
};

export type KycProviderCapabilities = {
  ocr: { enabled: boolean; provider: string; purpose: "extraction_only" };
  identity_verification: { enabled: boolean; provider: string; environment: "sandbox" | "live" | "disabled" };
};

export type CustomerKyc = { customer_id: string; current_status: string; verifications: KycVerification[] };
export type KycQueueItem = {
  id: string; customer_id: string; customer_reference: string; customer_name: string; national_id_masked: string;
  status: string; risk_level: string; verification_method: string; initiated_by_user_id: string;
  reviewed_by_user_id: string | null; created_at: string; reviewed_at: string | null; expires_at: string | null;
};
export type ApprovalQueueItem = {
  id: string; branch_id: string | null; aggregate_type: string; aggregate_id: string; aggregate_reference: string;
  action: string; version: number; requested_by_user_id: string; assigned_role: string; status: string;
  priority: string; request_reason: string; payload_snapshot: Record<string, unknown>; due_at: string | null;
  decided_by_user_id: string | null; decided_at: string | null; decision_reason: string | null; created_at: string;
  escalation_level: number; escalated_at: string | null; decided_under_delegation_id: string | null;
  events: Array<{ id: string; event_type: string; actor_user_id: string | null; from_status: string | null; to_status: string; reason: string | null; occurred_at: string }>;
};
export type ApprovalDelegation = {
  id: string; delegator_user_id: string; delegate_user_id: string; delegate_name: string;
  branch_id: string | null; assigned_role: string; starts_at: string; ends_at: string;
  reason: string; revoked_at: string | null; created_at: string;
};
export type InventoryCheckDetail = {
  id: string;
  location: { id: string; code: string; name: string };
  status: string;
  performed_by_user_id: string;
  reviewed_by_user_id: string | null;
  recounted_by_user_id: string | null;
  counted_at: string;
  recounted_at: string | null;
  approved_at: string | null;
  assets: Array<{
    application_id: string;
    application_no: string;
    asset_code: string;
    asset_label: string;
    expected_status: string | null;
    observed_status: string | null;
    result: string | null;
    note: string | null;
    recount_observed_status: string | null;
    recount_note: string | null;
  }>;
};
export type JournalItem = {
  id: string; entry_no: string; event_type: string; description: string; status: string;
  application_id: string | null; reversal_of_id: string | null; posted_at: string;
  total_debit: number; total_credit: number;
  lines: Array<{ account_code: string; account_name: string; debit: number; credit: number; description: string | null }>;
};
export type AccountingPeriod = {
  id: string; period_start: string; period_end: string; status: string; close_reason: string | null;
  closed_by_user_id: string | null; closed_at: string | null;
};
export type CustodyMovement = {
  id: string; movement_no: string; application_id: string; from_location_id: string; to_location_id: string;
  status: string; reason: string; seal_out: string | null; seal_in: string | null; created_at: string;
};
export type CollectionCaseDetail = {
  id: string; status: string; strategy: string; stage: string; aging_bucket: string; due_at: string;
  days_past_due: number; outstanding_amount: number; next_action_at: string | null; last_contact_at: string | null;
  assigned_user_id: string | null;
  loan: { id: string; account_no: string; application_id: string; application_no: string; status: string; principal_amount: number; outstanding_principal: number; outstanding_fee: number };
  borrower: { id: string; name: string; phone_masked: string };
  branch: { id: string; code: string; name: string };
  collateral: { asset_code: string; category: string; label: string; status: string; indicative_value: number };
  notes: Array<{ id: string; actor_user_id: string; channel: string; note: string; outcome: string; next_action_at: string | null; created_at: string }>;
  promises: Array<{ id: string; amount: number; promised_at: string; channel: string; status: string; note: string; resolution_reason: string | null; resolved_at: string | null; is_overdue: boolean; created_at: string }>;
};
export type IncidentListItem = {
  id: string; application_id: string; application_no: string; borrower_name: string;
  branch_code: string; branch_name: string; incident_type: string; severity: string; status: string;
  description: string; assigned_to_user_id: string | null; assigned_to_name: string | null;
  due_at: string | null; is_overdue: boolean; created_at: string;
};
export type IncidentDetail = {
  id: string;
  application: { id: string; application_no: string; borrower_name: string; branch_id: string; branch_code: string; branch_name: string };
  asset: { asset_code: string; label: string; collateral_status: string };
  incident_type: string; severity: string; status: string; description: string;
  reported_by_user_id: string; assigned_to_user_id: string | null; root_cause: string | null;
  action_plan: string | null; due_at: string | null; resolution_note: string | null;
  resolved_by_user_id: string | null; resolved_at: string | null; reopened_count: number; created_at: string;
  events: Array<{ id: string; event_type: string; actor_user_id: string | null; from_status: string | null; to_status: string | null; note: string | null; metadata: Record<string, unknown>; occurred_at: string }>;
};
export type ComplaintListItem = {
  id: string; ticket_no: string; borrower_id: string; borrower_name: string; branch_id: string; branch_code: string;
  category: string; channel: string; priority: string; status: string; subject: string;
  assigned_to_name: string | null; response_due_at: string; resolution_due_at: string;
  response_overdue: boolean; resolution_overdue: boolean; vulnerable_customer: boolean;
  regulator_reportable: boolean; escalation_level: number; created_at: string;
};
export type ComplaintDetail = {
  id: string; ticket_no: string; borrower: { id: string; name: string };
  branch: { id: string; code: string; name: string }; application_id: string | null;
  reported_by_user_id: string; assigned_to_user_id: string | null; category: string; channel: string;
  priority: string; status: string; subject: string; description: string; vulnerable_customer: boolean;
  regulator_reportable: boolean; response_due_at: string; resolution_due_at: string;
  acknowledged_at: string | null; resolution_summary: string | null; outcome: string | null;
  compensation_amount: number; resolved_by_user_id: string | null; resolved_at: string | null;
  escalation_level: number; reopened_count: number; created_at: string;
  events: Array<{ id: string; event_type: string; actor_user_id: string | null; direction: string | null;
    channel: string | null; from_status: string | null; to_status: string | null; message: string | null; occurred_at: string }>;
};
export type ConfigurationEvent = {
  id: string; event_type: string; actor_user_id: string | null; from_status: string | null;
  to_status: string | null; reason: string | null; occurred_at: string;
};
export type ConfigurationVersion = {
  id: string; domain: string; config_key: string; version: number; status: string;
  effective_from: string; effective_until: string | null; payload: Record<string, unknown>;
  checksum_sha256: string; change_summary: string; created_by_user_id: string;
  approved_by_user_id: string | null; approved_at: string | null; activated_at: string | null;
  supersedes_id: string | null; created_at: string; events?: ConfigurationEvent[];
};
export type ConfigurationPreview = {
  configuration_id: string; current_version: number | null; candidate_version: number;
  changed_field_count: number; effective_from: string;
  changes: Array<{ field: string; before: unknown; after: unknown }>;
  impact: { domain: string; key: string; requires_approval: boolean; supersedes_id: string | null };
};
export type PaymentAccount = {
  id: string; account_no: string; application_id: string; application_no: string; borrower_name: string;
  branch_id: string; branch_code: string; status: string; outstanding_principal: number;
  outstanding_fee: number; total_outstanding: number; paid_amount: number; due_at: string | null;
};
export type PaymentReceipt = {
  id: string; loan_account_id: string; account_no: string; application_id: string; application_no: string;
  receipt_no: string; channel: string; amount: number; allocated_fee: number; allocated_principal: number;
  status: string; external_reference: string; received_by_user_id: string; occurred_at: string;
};
export type PaymentAdjustment = {
  id: string; loan_account_id: string; payment_receipt_id: string | null; adjustment_type: string;
  component: string; amount: number; allocated_fee: number; allocated_principal: number; status: string;
  reason: string; external_reference: string; requested_by_user_id: string; approved_by_user_id: string | null;
  posted_at: string | null; created_at: string;
};
export type ReconciliationRun = {
  id: string; branch_id: string | null; scope: string; business_date: string; status: string;
  expected_amount: number; observed_amount: number; variance_amount: number; tolerance_amount: number;
  exception_count: number; snapshot: Record<string, unknown>; resolution_note: string | null;
  resolved_by_user_id: string | null; resolved_at: string | null; created_at: string;
};

export const listBranches = () => apiFetch<BranchItem[]>("/v1/master/branches");
export const listAssetCategories = () =>
  apiFetch<AssetCategoryItem[]>("/v1/master/asset-categories");
export const listLoanProducts = () =>
  apiFetch<LoanProductItem[]>("/v1/master/loan-products");
export const listCustodyLocations = () =>
  apiFetch<MasterItem[]>("/v1/master/custody-locations");
export const listStaffAssignments = () =>
  apiFetch<StaffAssignmentItem[]>("/v1/master/staff-assignments");
export const createBranch = (json: Record<string, unknown>) =>
  apiFetch<BranchItem>("/v1/master/branches", { method: "POST", json });
export const createAssetCategory = (json: Record<string, unknown>) =>
  apiFetch<AssetCategoryItem>("/v1/master/asset-categories", { method: "POST", json });
export const createLoanProduct = (json: Record<string, unknown>) =>
  apiFetch<LoanProductItem>("/v1/master/loan-products", { method: "POST", json });

export const getApplicationDetail = (id: string) =>
  apiFetch<ApplicationDetail>(`/v1/applications/${id}`);
export const createApplication = (json: Record<string, unknown>) =>
  apiFetch<ActionResult>("/v1/applications", { method: "POST", json });
export const getCollateralTimeline = (id: string) =>
  apiFetch<CollateralTimeline>(`/v1/collateral/${id}/timeline`);
export const transitionApplication = (id: string, to_status: string, note?: string) =>
  apiFetch<ActionResult>(`/v1/applications/${id}/transition`, {
    method: "POST",
    json: { to_status, note },
  });
export const createAppraisal = (json: Record<string, unknown>) =>
  apiFetch<ActionResult>("/v1/appraisals", { method: "POST", json });
export const createIncident = (json: Record<string, unknown>) =>
  apiFetch<ActionResult>("/v1/incidents", { method: "POST", json });
export const createOffer = (json: Record<string, unknown>) =>
  apiFetch<ActionResult>("/v1/offers", { method: "POST", json });
export const acceptOffer = (offerId: string) =>
  apiFetch<ActionResult>(`/v1/offers/${offerId}/accept`, {
    method: "POST",
    json: { channel: "branch" },
  });
export const createPickup = (json: Record<string, unknown>) =>
  apiFetch<ActionResult>("/v1/pickups", { method: "POST", json });
export const transitionPickup = (pickupId: string, to_status: string) =>
  apiFetch<ActionResult>(`/v1/pickups/${pickupId}/transition`, {
    method: "POST",
    json: { to_status },
  });
export const createCustodyEvent = (json: Record<string, unknown>) =>
  apiFetch<ActionResult>("/v1/custody/events", { method: "POST", json });
export const listCustodyMovements = () => apiFetch<CustodyMovement[]>("/v1/custody/movements");
export const requestCustodyMovement = (json: Record<string, unknown>) =>
  apiFetch<ActionResult>("/v1/custody/movements", { method: "POST", json });
export const dispatchCustodyMovement = (id: string, seal_out: string, note: string) =>
  apiFetch<ActionResult>(`/v1/custody/movements/${id}/dispatch`, { method: "POST", json: { seal_out, note } });
export const receiveCustodyMovement = (id: string, seal_in: string, note: string) =>
  apiFetch<ActionResult>(`/v1/custody/movements/${id}/receive`, { method: "POST", json: { seal_in, note } });
export const disburseLoan = (applicationId: string, external_reference: string) =>
  apiFetch<ActionResult>(`/v1/loans/${applicationId}/disburse`, {
    method: "POST",
    json: { external_reference, idempotency_key: `disbursement-${applicationId}-${external_reference}` },
  });
export const verifySettlement = (json: Record<string, unknown>) =>
  apiFetch<ActionResult>("/v1/settlements", { method: "POST", json });
export const listFieldTasks = () => apiFetch<FieldTaskItem[]>("/v1/field/tasks");
export const getPublicIntakeConfig = (slug: string) =>
  apiFetch<PublicIntakeConfig>(`/public/v1/partners/${slug}/intake-config`);
export const submitPublicApplication = (slug: string, json: Record<string, unknown>) =>
  apiFetch<ActionResult>(`/public/v1/partners/${slug}/applications`, { method: "POST", json });
export const uploadEvidence = (
  applicationId: string,
  file: File,
  evidenceType = "asset_photo",
  subjectType: EvidenceItem["subject_type"] = "application",
  subjectId?: string,
) => {
  const form = new FormData();
  form.append("evidence_type", evidenceType);
  form.append("subject_type", subjectType);
  if (subjectId) form.append("subject_id", subjectId);
  form.append("file", file);
  return apiUpload<ActionResult>(`/v1/applications/${applicationId}/evidence/upload`, form);
};
export const listEvidence = (applicationId: string, subjectType?: EvidenceItem["subject_type"], subjectId?: string) => {
  const query = new URLSearchParams();
  if (subjectType) query.set("subject_type", subjectType);
  if (subjectId) query.set("subject_id", subjectId);
  return apiFetch<EvidenceItem[]>(`/v1/applications/${applicationId}/evidence${query.size ? `?${query}` : ""}`);
};
export const downloadEvidence = (evidenceId: string) => apiDownload(`/v1/evidence/${evidenceId}/download`);
export const getFinanceOverview = () => apiFetch<FinanceOverview>("/v1/finance/overview");
export const listCashboxes = () => apiFetch<Array<Record<string, unknown>>>("/v1/finance/cashboxes");
export const listTellerSessions = () =>
  apiFetch<Array<Record<string, unknown>>>("/v1/finance/teller-sessions");
export const openTellerSession = (cashbox_id: string) =>
  apiFetch<ActionResult>("/v1/finance/teller-sessions", { method: "POST", json: { cashbox_id } });
export const closeTellerSession = (sessionId: string, actual_closing_balance: number, variance_reason?: string) =>
  apiFetch<ActionResult>(`/v1/finance/teller-sessions/${sessionId}/close`, {
    method: "POST",
    json: { actual_closing_balance, variance_reason },
  });
export const getFinancialReports = () => apiFetch<FinancialReports>("/v1/accounting/reports");
export const listJournals = () => apiFetch<JournalItem[]>("/v1/accounting/journals");
export const requestJournalReversal = (id: string, reason: string) =>
  apiFetch<ActionResult>(`/v1/accounting/journals/${id}/reverse`, {
    method: "POST",
    json: { reason, idempotency_key: `reversal-${id}-${Date.now()}` },
  });
export const listAccountingPeriods = () => apiFetch<AccountingPeriod[]>("/v1/accounting/periods");
export const createAccountingPeriod = (period_start: string, period_end: string) =>
  apiFetch<ActionResult>("/v1/accounting/periods", { method: "POST", json: { period_start, period_end } });
export const requestAccountingPeriodClose = (id: string, reason: string) =>
  apiFetch<ActionResult>(`/v1/accounting/periods/${id}/close`, { method: "POST", json: { reason } });
export const listCollections = () => apiFetch<Array<Record<string, unknown>>>("/v1/collections");
export const listIncidents = () => apiFetch<IncidentListItem[]>("/v1/incidents");
export const getIncident = (id: string) => apiFetch<IncidentDetail>(`/v1/incidents/${id}`);
export const triageIncident = (id: string, json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/incidents/${id}/triage`, { method: "POST", json });
export const addIncidentNote = (id: string, note: string) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/incidents/${id}/notes`, { method: "POST", json: { note } });
export const requestIncidentResolution = (id: string, resolution_note: string) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/incidents/${id}/resolution`, { method: "POST", json: { resolution_note } });
export const reopenIncident = (id: string, reason: string) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/incidents/${id}/reopen`, { method: "POST", json: { reason } });
export const listComplaints = () => apiFetch<ComplaintListItem[]>("/v1/complaints");
export const getComplaint = (id: string) => apiFetch<ComplaintDetail>(`/v1/complaints/${id}`);
export const createComplaint = (json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string; ticket_no: string }>("/v1/complaints", { method: "POST", json });
export const assignComplaint = (id: string, assigned_to_user_id: string, reason: string) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/complaints/${id}/assign`, { method: "POST", json: { assigned_to_user_id, reason } });
export const addComplaintCommunication = (id: string, json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/complaints/${id}/communications`, { method: "POST", json });
export const requestComplaintResolution = (id: string, json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/complaints/${id}/resolution`, { method: "POST", json });
export const reopenComplaint = (id: string, reason: string) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/complaints/${id}/reopen`, { method: "POST", json: { reason } });
export const escalateComplaintSla = () =>
  apiFetch<{ count: number; message: string }>("/v1/complaints/escalate-overdue", { method: "POST" });
export const getCollectionCase = (id: string) => apiFetch<CollectionCaseDetail>(`/v1/collections/${id}`);
export const addCollectionNote = (id: string, json: Record<string, unknown>) =>
  apiFetch<ActionResult>(`/v1/collections/${id}/notes`, { method: "POST", json });
export const updateCollectionPlan = (id: string, json: Record<string, unknown>) =>
  apiFetch<ActionResult>(`/v1/collections/${id}/plan`, { method: "PATCH", json });
export const createCollectionPromise = (id: string, json: Record<string, unknown>) =>
  apiFetch<ActionResult>(`/v1/collections/${id}/promises`, { method: "POST", json });
export const resolveCollectionPromise = (caseId: string, promiseId: string, status: string, reason: string) =>
  apiFetch<ActionResult>(`/v1/collections/${caseId}/promises/${promiseId}/resolve`, { method: "POST", json: { status, reason } });
export const listRegulatoryTemplates = () =>
  apiFetch<Array<Record<string, unknown>>>("/v1/regulatory/templates");
export const listRegulatoryRuns = () => apiFetch<Array<Record<string, unknown>>>("/v1/regulatory/runs");
export const createRegulatoryRun = (template_id: string, period_start: string, period_end: string) =>
  apiFetch<ActionResult>("/v1/regulatory/runs", {
    method: "POST",
    json: { template_id, period_start, period_end },
  });
export const submitRegulatoryTemplateActivation = (id: string, reason: string) =>
  apiFetch<ActionResult>(`/v1/regulatory/templates/${id}/submit-for-activation`, { method: "POST", json: { reason } });
export const submitRegulatoryRun = (id: string, reason: string) =>
  apiFetch<ActionResult>(`/v1/regulatory/runs/${id}/submit-for-approval`, {
    method: "POST",
    json: { reason },
  });
export const downloadRegulatoryRun = (id: string) => apiDownload(`/v1/regulatory/runs/${id}/export`);
export const listCustomers = () => apiFetch<CustomerListItem[]>("/v1/customers");
export const getCustomerDetail = (id: string) => apiFetch<CustomerDetail>(`/v1/customers/${id}`);
export const getCustomerKyc = (id: string) => apiFetch<CustomerKyc>(`/v1/customers/${id}/kyc`);
export const listKycVerifications = () => apiFetch<KycQueueItem[]>("/v1/kyc/verifications");
export const getKycProviderCapabilities = () => apiFetch<KycProviderCapabilities>("/v1/kyc/provider-capabilities");
export const startCustomerKyc = (id: string, json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/customers/${id}/kyc`, { method: "POST", json });
export const uploadKycDocument = (customerId: string, verificationId: string, file: File, documentSide = "ktp_front") => {
  const form = new FormData(); form.append("document_side", documentSide); form.append("file", file);
  return apiUpload<ActionResult>(`/v1/customers/${customerId}/kyc/${verificationId}/documents`, form);
};
export const reviewCustomerKyc = (customerId: string, verificationId: string, json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/customers/${customerId}/kyc/${verificationId}/review`, { method: "POST", json });
export const runKycOcr = (customerId: string, verificationId: string) =>
  apiFetch<{ id: string; status: string; officially_verified: boolean; message: string }>(`/v1/customers/${customerId}/kyc/${verificationId}/provider/ocr`, { method: "POST" });
export const runKycIdentityVerification = (customerId: string, verificationId: string) =>
  apiFetch<{ id: string; status: string; officially_verified: boolean; environment: string; message: string }>(`/v1/customers/${customerId}/kyc/${verificationId}/provider/identity-verification`, { method: "POST" });
export const listApprovals = () => apiFetch<ApprovalQueueItem[]>("/v1/approvals");
export const decideApproval = (id: string, decision: "approved" | "rejected", reason: string) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/approvals/${id}/decision`, { method: "POST", json: { decision, reason } });
export const listApprovalDelegations = () => apiFetch<ApprovalDelegation[]>("/v1/approvals/delegations");
export const createApprovalDelegation = (json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>("/v1/approvals/delegations", { method: "POST", json });
export const revokeApprovalDelegation = (id: string) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/approvals/delegations/${id}/revoke`, { method: "POST" });
export const runApprovalEscalations = () =>
  apiFetch<{ count: number; message: string }>("/v1/approvals/escalations/run", { method: "POST" });
export const listDomainEvents = (limit = 200) => apiFetch<DomainEvent[]>(`/v1/domain-events?limit=${limit}`);
export const listInventoryChecks = () => apiFetch<Array<Record<string, unknown>>>("/v1/inventory-checks");
export const createInventoryCheck = (location_id: string) =>
  apiFetch<ActionResult>("/v1/inventory-checks", { method: "POST", json: { location_id } });
export const getInventoryCheck = (id: string) =>
  apiFetch<InventoryCheckDetail>(`/v1/inventory-checks/${id}`);
export const submitInventoryCheck = (id: string, observations: Array<Record<string, unknown>>) =>
  apiFetch<ActionResult>(`/v1/inventory-checks/${id}/submit`, {
    method: "POST",
    json: { observations },
  });
export const recountInventoryCheck = (id: string, observations: Array<Record<string, unknown>>) =>
  apiFetch<ActionResult>(`/v1/inventory-checks/${id}/recount`, {
    method: "POST",
    json: { observations },
  });
export const listConfigurations = () => apiFetch<ConfigurationVersion[]>("/v1/configurations");
export const getConfiguration = (id: string) =>
  apiFetch<ConfigurationVersion>(`/v1/configurations/${id}`);
export const previewConfiguration = (id: string) =>
  apiFetch<ConfigurationPreview>(`/v1/configurations/${id}/preview`);
export const createConfiguration = (json: Record<string, unknown>) =>
  apiFetch<ActionResult>("/v1/configurations", { method: "POST", json });
export const updateConfiguration = (id: string, json: Record<string, unknown>) =>
  apiFetch<ActionResult>(`/v1/configurations/${id}`, { method: "PUT", json });
export const submitConfiguration = (id: string, reason: string) =>
  apiFetch<ActionResult>(`/v1/configurations/${id}/submit`, { method: "POST", json: { reason } });
export const cloneConfiguration = (id: string, effective_from: string, change_summary: string) =>
  apiFetch<ActionResult>(`/v1/configurations/${id}/clone`, {
    method: "POST", json: { effective_from, change_summary },
  });
export const applyDueConfigurations = () =>
  apiFetch<{ count: number; message: string }>("/v1/configurations/apply-due", { method: "POST" });
export const listPaymentAccounts = () => apiFetch<PaymentAccount[]>("/v1/finance/loan-accounts");
export const listPayments = () => apiFetch<PaymentReceipt[]>("/v1/finance/payments");
export const createPayment = (json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>("/v1/finance/payments", { method: "POST", json });
export const listPaymentAdjustments = () => apiFetch<PaymentAdjustment[]>("/v1/finance/payment-adjustments");
export const createPaymentAdjustment = (json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>("/v1/finance/payment-adjustments", { method: "POST", json });
export const listReconciliations = () => apiFetch<ReconciliationRun[]>("/v1/finance/reconciliations");
export const createReconciliation = (json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>("/v1/finance/reconciliations", { method: "POST", json });
export const requestReconciliationResolution = (id: string, resolution_note: string) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/finance/reconciliations/${id}/resolution`, { method: "POST", json: { resolution_note } });

