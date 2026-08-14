/**
 * Typed HTTP client for the FastAPI backend.
 *
 * Sends the current Firebase token automatically (see `lib/auth-token.ts`);
 * callers can override with an explicit `token` option (e.g. guest tokens).
 */
import { appConfig } from "@/config/env";
import { getAuthToken } from "@/lib/auth-token";
import { ApiError, type ApiErrorShape } from "@/lib/errors";

interface ApiClientOptions {
  /** Authorization token (Firebase ID token, guest token, or null). */
  token?: string | null;
  /** Custom timeout in ms. Default 15s. */
  timeoutMs?: number;
  /** Correlate retries/client journey with the server (docs/architecture/14). */
  requestId?: string;
  /** Send the body as-is without forcing a JSON Content-Type (multipart uploads). */
  multipart?: boolean;
}

export interface ApiResult<T> {
  data: T;
  status: number;
  requestId: string | undefined;
}

async function parseError(response: Response, text: string): Promise<ApiError> {
  let shape: ApiErrorShape = {
    code: "HTTP_ERROR",
    message: text || `Request failed with status ${response.status}.`,
  };
  try {
    const body = JSON.parse(text) as { error?: ApiErrorShape };
    if (body.error) shape = body.error;
  } catch {
    // non-JSON body — keep the HTTP fallback above
  }
  return new ApiError(shape, response.status);
}

/**
 * Core fetch wrapper. Handles envelope parsing, JSON errors, and timeouts.
 */
export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  options: ApiClientOptions = {},
): Promise<ApiResult<T>> {
  const { token = getAuthToken(), timeoutMs = 15_000, requestId, multipart = false } = options;
  const baseUrl = appConfig.apiBaseUrl.replace(/\/$/, "");
  const url = `${baseUrl}${path}`;

  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !multipart && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (requestId) headers.set("X-Request-Id", requestId);

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { ...init, headers, signal: controller.signal });
    const text = await response.text();
    if (!response.ok) {
      throw await parseError(response, text);
    }
    const data = (text ? JSON.parse(text) : {}) as T;
    return {
      data,
      status: response.status,
      requestId: response.headers.get("X-Request-Id") ?? undefined,
    };
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        { code: "TIMEOUT", message: "The request timed out. Please try again." },
        408,
      );
    }
    throw new ApiError(
      { code: "NETWORK_ERROR", message: "Network error. Check your connection." },
      0,
    );
  } finally {
    window.clearTimeout(timer);
  }
}

/** Typed GET helper. */
export function get<T>(
  path: string,
  options: ApiClientOptions = {},
): Promise<ApiResult<T>> {
  return apiRequest<T>(path, { method: "GET" }, options);
}

/** Typed POST helper. */
export function post<T>(
  path: string,
  body?: unknown,
  options: ApiClientOptions = {},
): Promise<ApiResult<T>> {
  return apiRequest<T>(
    path,
    { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) },
    options,
  );
}

/** Typed PUT helper. */
export function put<T>(
  path: string,
  body?: unknown,
  options: ApiClientOptions = {},
): Promise<ApiResult<T>> {
  return apiRequest<T>(
    path,
    { method: "PUT", body: body === undefined ? undefined : JSON.stringify(body) },
    options,
  );
}

/** Typed PATCH helper. */
export function patch<T>(
  path: string,
  body?: unknown,
  options: ApiClientOptions = {},
): Promise<ApiResult<T>> {
  return apiRequest<T>(
    path,
    { method: "PATCH", body: body === undefined ? undefined : JSON.stringify(body) },
    options,
  );
}

/** Typed DELETE helper. */
export function del<T>(
  path: string,
  options: ApiClientOptions = {},
): Promise<ApiResult<T>> {
  return apiRequest<T>(path, { method: "DELETE" }, options);
}
