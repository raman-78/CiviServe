/**
 * API error normalized from the backend error envelope
 * `{ error: { code, message, details, requestId } }` (docs/architecture/13).
 */
export interface ApiErrorShape {
  code: string;
  message: string;
  details?: Record<string, unknown> | unknown[];
  requestId?: string;
}

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown> | unknown[] | undefined;
  readonly requestId: string | undefined;

  constructor(shape: ApiErrorShape, status: number) {
    super(shape.message || shape.code);
    this.name = "ApiError";
    this.code = shape.code;
    this.status = status;
    this.details = shape.details;
    this.requestId = shape.requestId;
  }
}

/** True when `error` is one of our typed API errors. */
export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

/** Normalize any thrown value into a message-safe string for the UI. */
export function errorMessage(error: unknown): string {
  if (isApiError(error)) return error.message;
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Something went wrong. Please try again.";
}
