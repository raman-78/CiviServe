import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  MessageSquarePlus,
  MessagesSquare,
  Pencil,
  Search,
  Trash2,
  X,
} from "lucide-react";
import type { ChatSession } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface HistorySidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  loading: boolean;
  onSelect: (sessionId: string) => void;
  onNewChat: () => void;
  onSearch: (query: string) => void;
  onRename: (sessionId: string, title: string) => void;
  onDelete: (sessionId: string) => void;
}

/** Conversation history: list + search + inline rename/delete + new chat. */
export function HistorySidebar({
  sessions,
  activeSessionId,
  loading,
  onSelect,
  onNewChat,
  onSearch,
  onRename,
  onDelete,
}: HistorySidebarProps) {
  const { t } = useTranslation();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");

  const startRename = (session: ChatSession) => {
    setEditingId(session.id);
    setDraftTitle(session.title ?? "");
  };

  const submitRename = (sessionId: string) => {
    if (draftTitle.trim()) onRename(sessionId, draftTitle.trim());
    setEditingId(null);
  };

  return (
    <aside
      className="flex w-72 shrink-0 flex-col gap-3 border-r bg-muted/30 p-3"
      aria-label={t("chat.historyTitle")}
    >
      <Button type="button" onClick={onNewChat} className="w-full justify-start gap-2">
        <MessageSquarePlus className="h-4 w-4" />
        {t("chat.newChat")}
      </Button>

      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          onChange={(e) => onSearch(e.target.value)}
          placeholder={t("chat.searchSessions")}
          aria-label={t("chat.searchSessions")}
          className="pl-8"
        />
      </div>

      <div className="flex-1 space-y-1 overflow-y-auto">
        {loading ? (
          <p className="px-2 py-4 text-sm text-muted-foreground">{t("common.loading")}</p>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-2 py-6 text-center text-sm text-muted-foreground">
            <MessagesSquare className="h-5 w-5" />
            <p>{t("chat.emptySessions")}</p>
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={cn(
                "group flex items-center gap-1 rounded-md px-2 py-1.5 text-sm",
                session.id === activeSessionId
                  ? "bg-primary/10 font-medium text-primary"
                  : "hover:bg-muted",
              )}
            >
              {editingId === session.id ? (
                <Input
                  autoFocus
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") submitRename(session.id);
                    if (e.key === "Escape") setEditingId(null);
                  }}
                  className="h-7 flex-1"
                />
              ) : (
                <button
                  type="button"
                  className="flex-1 truncate text-left"
                  onClick={() => onSelect(session.id)}
                  title={session.title ?? undefined}
                >
                  {session.title || t("chat.untitled")}
                </button>
              )}

              {editingId === session.id ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => submitRename(session.id)}
                  aria-label={t("chat.done")}
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              ) : (
                <div className="hidden items-center gap-0.5 group-hover:flex">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => startRename(session)}
                    aria-label={t("chat.rename")}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-destructive"
                    onClick={() => onDelete(session.id)}
                    aria-label={t("chat.delete")}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </aside>
  );
}