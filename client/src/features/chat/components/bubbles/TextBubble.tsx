import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";

/** Plain text bubble; fallback renderer for simple content types. */
export function TextBubble({ message }: { message: ChatMessage }) {
  return (
    <div
      className={cn(
        "inline-block rounded-2xl px-4 py-2 text-sm leading-relaxed",
        message.role === "user"
          ? "rounded-br-sm bg-primary text-primary-foreground"
          : "rounded-bl-sm bg-muted",
      )}
    >
      {message.renderedText ?? message.content}
    </div>
  );
}
