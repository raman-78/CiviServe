/**
 * Module-level accessor for the current auth token so the HTTP client can send
 * a Bearer token without threading it through every call site. The AuthContext
 * updates this on every auth-state change.
 */
let currentToken: string | null = null;

export function setAuthToken(token: string | null): void {
  currentToken = token;
}

export function getAuthToken(): string | null {
  return currentToken;
}
