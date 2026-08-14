import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";
import { messageComponentRegistry } from "@/features/chat/messageRegistry";

interface ChatBubbleProps {
  message: ChatMessage;
  className?: string;
}

/** Renders one message via the content-type registry (docs/architecture/07). */
export function ChatBubble({ message, className }: ChatBubbleProps) {
  const Bubble = messageComponentRegistry[message.contentType] ?? messageComponentRegistry.text;

  return (
    <div
      data-role={message.role}
      className={cn(
        "flex w-full",
        message.role === "user" ? "justify-end" : "justify-start",
        className,
      )}
    >
      <div
        className={cn(
          "max-w-[85%]",
          message.role === "user" ? "text-right" : "text-left",
        )}
      >
        <Bubble message={message} />
      </div>
    </div>
  );
}
