/**
 * Typed API for the chat surface (sessions + messages + SSE streaming).
 *
 * Sync variants use the shared HTTP client; streaming reads ``fetch`` directly
 * because ``api-client`` buffers full bodies (unsuitable for text/event-stream).
 */
import { appConfig } from "@/config/env";
import { getAuthToken } from "@/lib/auth-token";
import { get, patch, del, post } from "@/lib/api-client";
import type { ApiResult } from "@/lib/api-client";
import { ApiError } from "@/lib/errors";
import type { Paginated } from "@/types";
import type { ChatMessage, ChatSession, MessageContentType } from "@/types";
import { clientId } from "@/lib/utils";

export interface SendMessagePayload {
  text: string;
  language?: string;
  contentType?: MessageContentType;
  clientRequestId?: string;
}

/** Create a new conversation. */
export async function createChatSession(
  payload: { language?: string; channel?: string; title?: string } = {},
): Promise<ApiResult<ChatSession>> {
  return post<ChatSession>("/api/v1/chat/sessions", payload);
}

/** Page through the caller's conversations (most-recent first). */
export async function listChatSessions(
  page = 1,
  pageSize = 50,
): Promise<ApiResult<Paginated<ChatSession>>> {
  return get<Paginated<ChatSession>>(
    `/api/v1/chat/sessions?page=${page}&page_size=${pageSize}`,
  );
}

/** Find sessions by title. */
export async function searchChatSessions(q: string): Promise<ApiResult<ChatSession[]>> {
  return get<ChatSession[]>(`/api/v1/chat/sessions/search?q=${encodeURIComponent(q)}`);
}

/** Get a single conversation. */
export async function getChatSession(sessionId: string): Promise<ApiResult<ChatSession>> {
  return get<ChatSession>(`/api/v1/chat/sessions/${sessionId}`);
}

/** Rename a conversation. */
export async function renameChatSession(
  sessionId: string,
  title: string,
): Promise<ApiResult<ChatSession>> {
  return patch<ChatSession>(`/api/v1/chat/sessions/${sessionId}`, { title });
}

/** Archive (soft-delete) a conversation. */
export async function deleteChatSession(sessionId: string): Promise<void> {
  await del<unknown>(`/api/v1/chat/sessions/${sessionId}`);
}

/** List messages for a conversation, chronological. */
export async function listChatMessages(
  sessionId: string,
  page = 1,
  pageSize = 200,
): Promise<ApiResult<Paginated<ChatMessage>>> {
  return get<Paginated<ChatMessage>>(
    `/api/v1/chat/sessions/${sessionId}/messages?page=${page}&page_size=${pageSize}`,
  );
}

/**
 * Send a turn and get the persisted assistant reply (blocking).
 * Passing the same `clientRequestId` is idempotent server-side.
 */
export async function sendChatMessage(
  sessionId: string,
  payload: SendMessagePayload,
): Promise<ApiResult<ChatMessage>> {
  return post<ChatMessage>(`/api/v1/chat/sessions/${sessionId}/messages`, payload);
}

export interface StreamListener {
  /** Live token as it arrives. */
  onToken?: (text: string) => void;
  /** Final persisted assistant message. */
  onMessage?: (message: ChatMessage) => void;
  onError?: (error: ApiError) => void;
}

/**
 * Stream one turn over SSE. Returns an abort function.
 * Events: `token` (raw chunk), `reply` (final message), `[DONE]`.
 */
export function streamChatMessage(
  sessionId: string,
  payload: SendMessagePayload,
  listener: StreamListener,
): () => void {
  const controller = new AbortController();
  const baseUrl = appConfig.apiBaseUrl.replace(/\/$/, "");
  const url = `${baseUrl}/api/v1/chat/sessions/${sessionId}/messages/stream`;

  void (async () => {
    try {
      const token = getAuthToken();
      const headers: Record<string, string> = {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
      };
      if (token) headers.Authorization = `Bearer ${token}`;

      const response = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        const text = await response.text().catch(() => "");
        throw new ApiError(
          { code: "HTTP_ERROR", message: text || `Request failed (${response.status}).` },
          response.status,
        );
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const consume = () => {
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const raw of lines) {
          const line = raw.trim();
          if (!line.startsWith("data:")) continue;
          const data = line.slice(5).trim();
          if (data === "[DONE]") return finish();
          try {
            const event = JSON.parse(data) as {
              type: "token" | "reply";
              text?: string;
              message?: ChatMessage;
            };
            if (event.type === "token" && event.text) listener.onToken?.(event.text);
            else if (event.type === "reply" && event.message) listener.onMessage?.(event.message);
          } catch {
            // Malformed SSE line — skip.
          }
        }
      };

      const finish = () => {
        reader.cancel().catch(() => undefined);
        controller.abort();
      };

      const pump = (): Promise<void> => {
        return reader.read().then(({ done, value }) => {
          if (done) return;
          buffer += decoder.decode(value, { stream: true });
          consume();
          return pump();
        });
      };

      await pump();
    } catch (error) {
      if (error instanceof ApiError) {
        listener.onError?.(error);
      } else if (!(error instanceof DOMException && error.name === "AbortError")) {
        listener.onError?.(
          new ApiError({ code: "NETWORK_ERROR", message: "Network error." }, 0),
        );
      }
    }
  })();

  return () => controller.abort();
}

/** Build a fresh clientRequestId per send (idempotency key). */
export function nextClientRequestId(): string {
  return clientId();
}