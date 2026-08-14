import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ChatWindow } from "@/features/chat/components/ChatWindow";
import { HistorySidebar } from "@/features/chat/components/HistorySidebar";
import {
  createChatSession,
  deleteChatSession,
  listChatMessages,
  listChatSessions,
  renameChatSession,
  searchChatSessions,
  streamChatMessage,
  type SendMessagePayload,
} from "@/features/chat/api";
import { useChatStore } from "@/store/chatSlice";
import { useSettingsStore } from "@/store/settingsSlice";
import { errorMessage } from "@/lib/errors";
import { clientId } from "@/lib/utils";
import type { ChatMessage, ChatSession } from "@/types";

/** Chat page: real sessions, history sidebar, SSE streaming replies. */
export function ChatPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { sessionId: routeSessionId } = useParams<{ sessionId: string }>();

  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const setActiveSessionId = useChatStore((s) => s.setActiveSessionId);
  const setAssistantTyping = useChatStore((s) => s.setAssistantTyping);
  const uiLanguage = useSettingsStore((s) => s.language);

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  const currentSessionId = routeSessionId ?? activeSessionId;

  // ---- Sessions (history sidebar) ----
  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const { data } = await listChatSessions(1, 100);
      setSessions(data.items ?? []);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  // ---- Messages for the active session ----
  const loadMessages = useCallback(async (sessionId: string) => {
    setMessagesLoading(true);
    try {
      const { data } = await listChatMessages(sessionId, 1, 200);
      setMessages(data.items ?? []);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (currentSessionId) {
      void loadMessages(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId, loadMessages]);

  // ---- Streaming helpers ----
  const appendUserMessage = useCallback(
    (sessionId: string, text: string): ChatMessage => {
      const message: ChatMessage = {
        id: clientId(),
        sessionId,
        role: "user",
        contentType: "text",
        content: text,
        language: uiLanguage,
        status: "complete",
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, message]);
      return message;
    },
    [uiLanguage],
  );

  const appendAssistantPlaceholder = useCallback(
    (sessionId: string): ChatMessage => {
      const message: ChatMessage = {
        id: clientId(),
        sessionId,
        role: "assistant",
        contentType: "text",
        content: "",
        language: "en",
        status: "processing",
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, message]);
      return message;
    },
    [],
  );

  const replaceAssistantMessage = useCallback((replacement: ChatMessage) => {
    setMessages((prev) =>
      prev.map((m) => (m.status === "processing" && m.id === replacement.id ? replacement : m)),
    );
  }, []);

  const handleSend = useCallback(
    async (text: string) => {
      let sessionId = currentSessionId;
      if (!sessionId) {
        try {
          const { data } = await createChatSession({ language: uiLanguage, channel: "web" });
          sessionId = data.id;
          setActiveSessionId(sessionId);
          navigate(`/chat/${sessionId}`, { replace: true });
          setSessions((prev) => [data, ...prev]);
        } catch (error) {
          toast.error(errorMessage(error));
          return;
        }
      }

      appendUserMessage(sessionId, text);

      const placeholder = appendAssistantPlaceholder(sessionId);
      const requestId = clientId();
      const payload: SendMessagePayload = {
        text,
        language: uiLanguage,
        contentType: "text",
        clientRequestId: requestId,
      };

      setIsStreaming(true);
      setAssistantTyping(true);

      streamChatMessage(sessionId, payload, {
        onToken: (chunk) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === placeholder.id
                ? { ...m, content: m.content + chunk, status: "processing" }
                : m,
            ),
          );
        },
        onMessage: (message) => {
          setIsStreaming(false);
          setAssistantTyping(false);
          replaceAssistantMessage({ ...message, id: placeholder.id });
        },
        onError: (error) => {
          setIsStreaming(false);
          setAssistantTyping(false);
          replaceAssistantMessage({
            ...placeholder,
            status: "failed",
            content: error.message,
          });
          toast.error(error.message);
        },
      });
    },
    [
      currentSessionId,
      uiLanguage,
      navigate,
      setActiveSessionId,
      setAssistantTyping,
      appendUserMessage,
      appendAssistantPlaceholder,
      replaceAssistantMessage,
    ],
  );

  const handlePickQuestion = useCallback(
    (question: string) => {
      void handleSend(question);
    },
    [handleSend],
  );

  const handleRegenerate = useCallback(
    async (message: ChatMessage) => {
      const text = message.content || message.renderedText || "";
      if (!text) return;
      setMessages((prev) => prev.filter((m) => m.id !== message.id));
      await handleSend(text);
    },
    [handleSend],
  );

  const handleRetry = useCallback(
    async (message: ChatMessage) => {
      const text = message.content || message.renderedText || "";
      if (!text) return;
      setMessages((prev) => prev.filter((m) => m.id !== message.id));
      await handleSend(text);
    },
    [handleSend],
  );

  // ---- Sidebar actions ----
  const handleSelectSession = useCallback(
    (sessionId: string) => {
      setActiveSessionId(sessionId);
      navigate(`/chat/${sessionId}`);
    },
    [navigate, setActiveSessionId],
  );

  const handleNewChat = useCallback(() => {
    setActiveSessionId(null);
    navigate("/chat");
  }, [navigate, setActiveSessionId]);

  const handleSearch = useCallback(
    async (query: string) => {
      if (!query.trim()) {
        await loadSessions();
        return;
      }
      try {
        const { data } = await searchChatSessions(query.trim());
        setSessions(data);
      } catch (error) {
        toast.error(errorMessage(error));
      }
    },
    [loadSessions],
  );

  const handleRename = useCallback(
    async (sessionId: string, title: string) => {
      try {
        const { data } = await renameChatSession(sessionId, title);
        setSessions((prev) => prev.map((s) => (s.id === sessionId ? data : s)));
      } catch (error) {
        toast.error(errorMessage(error));
      }
    },
    [],
  );

  const handleDelete = useCallback(
    async (sessionId: string) => {
      try {
        await deleteChatSession(sessionId);
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        if (currentSessionId === sessionId) {
          setActiveSessionId(null);
          navigate("/chat");
        }
      } catch (error) {
        toast.error(errorMessage(error));
      }
    },
    [currentSessionId, navigate, setActiveSessionId],
  );

  const header = useMemo(() => {
    const session = sessions.find((s) => s.id === currentSessionId);
    return session?.title ?? (currentSessionId ? t("chat.title") : t("chat.startNew"));
  }, [sessions, currentSessionId, t]);

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-4">
      <HistorySidebar
        sessions={sessions}
        activeSessionId={currentSessionId}
        loading={sessionsLoading}
        onSelect={handleSelectSession}
        onNewChat={handleNewChat}
        onSearch={handleSearch}
        onRename={handleRename}
        onDelete={handleDelete}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="mb-4 border-b pb-3">
          <h1 className="truncate text-lg font-semibold">{header}</h1>
        </div>
        <ChatWindow
          messages={messages}
          onSend={(text) => void handleSend(text)}
          disabled={isStreaming || messagesLoading}
          onPickQuestion={handlePickQuestion}
          onRegenerate={handleRegenerate}
          onRetry={handleRetry}
        />
      </div>
    </div>
  );
}