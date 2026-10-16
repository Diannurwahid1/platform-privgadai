import { apiFetch } from "@/lib/api";
import type { LoginInput, RegisterInput } from "@/lib/validators";

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  email_verified_at: string | null;
  is_superadmin: boolean;
  is_active: boolean;
  created_at: string;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type RegisterResponse = {
  user: User;
  tokens: TokenPair;
  email_verification_link: string | null;
};

export const login = (input: LoginInput) =>
  apiFetch<TokenPair>("/auth/login", { method: "POST", json: input });

export const register = (input: RegisterInput) =>
  apiFetch<RegisterResponse>("/auth/register", { method: "POST", json: input });

export const me = () => apiFetch<User>("/auth/me");

export const logout = () =>
  apiFetch<{ detail: string }>("/auth/logout", { method: "POST" });

export const verifyEmail = (token: string) =>
  apiFetch<{ detail: string }>("/auth/verify-email", {
    method: "POST",
    json: { token },
  });

export type SecurityOverview = {
  mfa_enabled: boolean;
  mfa_activated_at: string | null;
  recovery_codes_remaining: number;
  current_session_id: string | null;
};
export type AuthSessionItem = {
  id: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  revoked_at: string | null;
  revoke_reason: string | null;
  mfa_authenticated: boolean;
  step_up_until: string | null;
  is_current: boolean;
  is_active: boolean;
};
export type SecurityEventItem = {
  id: string;
  event_type: string;
  severity: string;
  outcome: string;
  description: string;
  ip_address: string | null;
  user_agent: string | null;
  event_metadata: Record<string, unknown>;
  occurred_at: string;
};
export const getSecurityOverview = () => apiFetch<SecurityOverview>("/auth/security");
export const listAuthSessions = () => apiFetch<AuthSessionItem[]>("/auth/sessions");
export const listSecurityEvents = () => apiFetch<SecurityEventItem[]>("/auth/security-events");
export const setupMfa = (password: string) =>
  apiFetch<{ secret: string; otpauth_uri: string }>("/auth/mfa/setup", { method: "POST", json: { password } });
export const activateMfa = (code: string) =>
  apiFetch<{ enabled: boolean; recovery_codes: string[] }>("/auth/mfa/activate", { method: "POST", json: { code } });
export const stepUpAuthentication = (password: string, mfa_code?: string) =>
  apiFetch<{ session_id: string; step_up_until: string; status: string }>("/auth/step-up", {
    method: "POST",
    json: { password, mfa_code: mfa_code || undefined },
  });
export const revokeAuthSession = (id: string, reason: string) =>
  apiFetch<{ id: string; status: string; revoked_at: string }>(`/auth/sessions/${id}/revoke`, {
    method: "POST",
    json: { reason },
  });
