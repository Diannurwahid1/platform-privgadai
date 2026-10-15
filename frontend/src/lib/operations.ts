import { apiFetch } from "@/lib/api";

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

