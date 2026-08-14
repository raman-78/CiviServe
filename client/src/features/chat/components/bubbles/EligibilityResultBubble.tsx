import { Badge } from "@/components/ui/badge";
import type { ChatMessage } from "@/types";

/** Eligibility verdict rendered from a structured payload. */
export function EligibilityResultBubble({ message }: { message: ChatMessage }) {
  const payload = (message.payload ?? {}) as {
    eligible?: boolean;
    score?: number;
    reasons?: string[];
  };

  const eligible = payload.eligible;

  return (
    <div className="w-full max-w-md rounded-2xl rounded-bl-sm border bg-background p-4">
      <div className="flex items-center gap-2">
        {eligible === undefined ? (
          <Badge variant="muted">{message.renderedText ?? message.content}</Badge>
        ) : (
          <Badge variant={eligible ? "success" : "warning"}>
            {eligible ? "Likely eligible" : "May not qualify"}
          </Badge>
        )}
        {payload.score !== undefined ? (
          <span className="text-xs text-muted-foreground">{Math.round(payload.score)}% match</span>
        ) : null}
      </div>
      {payload.reasons && payload.reasons.length > 0 ? (
        <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
          {payload.reasons.map((reason, index) => (
            <li key={index} className="flex gap-2">
              <span aria-hidden>•</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
