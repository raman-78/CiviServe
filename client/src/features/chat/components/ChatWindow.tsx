import { useTranslation } from "react-i18next";
import type { ChatMessage } from "@/types";
import { MessageList } from "@/features/chat/components/MessageList";
import { ChatInput } from "@/features/chat/components/ChatInput";
import { EmptyState } from "@/components/shared/EmptyState";
import { MessagesSquare } from "lucide-react";

interface ChatWindowProps {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  disabled?: boolean;
  onPickQuestion?: (text: string) => void;
  onRegenerate?: (message: ChatMessage) => void;
  onRetry?: (message: ChatMessage) => void;
}

/** Chat page scaffold: message list + composer (docs/architecture/07). */
export function ChatWindow({
  messages,
  onSend,
  disabled,
  onPickQuestion,
  onRegenerate,
  onRetry,
}: ChatWindowProps) {
  const { t } = useTranslation();

  return (
    <div className="flex h-full min-h-[60vh] flex-col">
      {messages.length === 0 ? (
        <div className="flex flex-1 items-center justify-center py-16">
          <EmptyState
            icon={MessagesSquare}
            title={t("chat.emptyTitle")}
            description={t("chat.emptyDescription")}
          />
        </div>
      ) : (
        <MessageList
          messages={messages}
          className="flex-1 overflow-y-auto pb-4"
          onPickQuestion={onPickQuestion}
          onRegenerate={onRegenerate}
          onRetry={onRetry}
        />
      )}
      <ChatInput onSend={onSend} disabled={disabled} />
      <p className="mt-2 px-1 text-center text-[11px] leading-snug text-muted-foreground">
        {t("chat.disclaimer")}
      </p>
    </div>
  );
}