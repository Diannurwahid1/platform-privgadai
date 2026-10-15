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
  counted_at: string;
  approved_at: string | null;
  assets: Array<{
    application_id: string;
    application_no: string;
    asset_code: string;
    asset_label: string;
    expected_status: string;
    observed_status: string | null;
    result: string | null;
    note: string | null;
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
export const uploadEvidence = (applicationId: string, file: File, evidenceType = "asset_photo") => {
  const form = new FormData();
  form.append("evidence_type", evidenceType);
  form.append("file", file);
  return apiUpload<ActionResult>(`/v1/applications/${applicationId}/evidence/upload`, form);
};
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
export const startCustomerKyc = (id: string, json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/customers/${id}/kyc`, { method: "POST", json });
export const uploadKycDocument = (customerId: string, verificationId: string, file: File, documentSide = "ktp_front") => {
  const form = new FormData(); form.append("document_side", documentSide); form.append("file", file);
  return apiUpload<ActionResult>(`/v1/customers/${customerId}/kyc/${verificationId}/documents`, form);
};
export const reviewCustomerKyc = (customerId: string, verificationId: string, json: Record<string, unknown>) =>
  apiFetch<{ id: string; status: string; message: string }>(`/v1/customers/${customerId}/kyc/${verificationId}/review`, { method: "POST", json });
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

