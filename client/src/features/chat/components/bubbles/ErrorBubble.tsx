import { AlertTriangle } from "lucide-react";
import type { ChatMessage } from "@/types";

/** Failed assistant turn. */
export function ErrorBubble({ message }: { message: ChatMessage }) {
  return (
    <div
      role="alert"
      className="inline-flex items-center gap-2 rounded-2xl rounded-bl-sm border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive"
    >
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>{message.renderedText ?? message.content}</span>
    </div>
  );
}
