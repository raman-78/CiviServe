import { Card } from "@/components/ui/card";
import type { ChatMessage } from "@/types";

interface SchemeListItem {
  code?: string;
  name?: string;
}

/** Rich "scheme-list" payload: a compact set of scheme references. */
export function SchemeListBubble({ message }: { message: ChatMessage }) {
  const payload = (message.payload ?? {}) as {
    schemes?: SchemeListItem[];
  };

  const schemes = payload.schemes ?? [];

  return (
    <div className="w-full max-w-md space-y-2">
      {message.renderedText ?? message.content ? (
        <p className="text-sm text-muted-foreground">
          {message.renderedText ?? message.content}
        </p>
      ) : null}
      {schemes.length === 0 ? (
        <Card className="px-4 py-3 text-sm">{message.renderedText ?? message.content}</Card>
      ) : (
        schemes.map((scheme, index) => (
          <Card key={`${scheme.code}-${index}`} className="flex items-center justify-between px-4 py-3">
            <span className="text-sm font-medium">{scheme.name}</span>
            {scheme.code ? (
              <span className="text-xs text-muted-foreground">{scheme.code}</span>
            ) : null}
          </Card>
        ))
      )}
    </div>
  );
}
