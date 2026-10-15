import { apiFetch, apiUpload } from "@/lib/api";

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
  min_amount: number;
  max_amount: number;
  max_ltv_percent: number;
  allowed_tenors_days: number[];
  service_fee_percent: number;
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
export const disburseLoan = (applicationId: string, external_reference: string) =>
  apiFetch<ActionResult>(`/v1/loans/${applicationId}/disburse`, {
    method: "POST",
    json: { external_reference },
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

