/**
 * Thin HTTP client that proxies through the Next.js BFF route at
 * /api/backend/* so the browser never speaks to the FastAPI service
 * directly and cookies stay first-party.
 *
 * authx issues CSRF cookies (`csrf_access_token`, `csrf_refresh_token`) at
 * login/refresh time and requires their value to be echoed back in the
 * `X-CSRF-TOKEN` header on every cookie-authenticated mutating request
 * (POST/PUT/PATCH/DELETE). We read the cookie client-side and attach it
 * automatically.
 */

const BFF_PREFIX = "/api/backend";

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export type ApiError = {
  status: number;
  detail: string;
};

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : undefined;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const { json, headers, ...rest } = init ?? {};
  const method = (rest.method ?? "GET").toUpperCase();

  const csrfHeaders: Record<string, string> = {};
  if (MUTATING_METHODS.has(method)) {
    const cookieName = path.startsWith("/auth/refresh")
      ? "csrf_refresh_token"
      : "csrf_access_token";
    const token = readCookie(cookieName);
    if (token) csrfHeaders["X-CSRF-TOKEN"] = token;
  }

  const response = await fetch(`${BFF_PREFIX}${path}`, {
    ...rest,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...csrfHeaders,
      ...(headers ?? {}),
    },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body?.detail ?? body?.msg ?? detail;
    } catch {
      // body wasn't JSON; keep statusText
    }
    const err: ApiError = { status: response.status, detail };
    throw err;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const token = readCookie("csrf_access_token");
  const response = await fetch(`${BFF_PREFIX}${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(token ? { "X-CSRF-TOKEN": token } : {}),
    },
    body: form,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body?.detail ?? body?.msg ?? detail;
    } catch {}
    throw { status: response.status, detail } as ApiError;
  }
  return (await response.json()) as T;
}

export async function apiDownload(path: string): Promise<void> {
  const response = await fetch(`${BFF_PREFIX}${path}`, { credentials: "include" });
  if (!response.ok) {
    let detail = response.statusText;
    try { detail = (await response.json())?.detail ?? detail; } catch {}
    throw { status: response.status, detail } as ApiError;
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const fileName = disposition.match(/filename="?([^";]+)"?/)?.[1] ?? "regulatory-package.zip";
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}
