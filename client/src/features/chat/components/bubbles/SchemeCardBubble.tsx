import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ChatMessage } from "@/types";

/** Rich "scheme-card" payload rendered inside the conversation. */
export function SchemeCardBubble({ message }: { message: ChatMessage }) {
  const payload = (message.payload ?? {}) as {
    code?: string;
    name?: string;
    summary?: string;
    category?: string;
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          {payload.category ? <Badge variant="secondary">{payload.category}</Badge> : null}
          {payload.code ? <span className="text-xs text-muted-foreground">{payload.code}</span> : null}
        </div>
        <CardTitle className="text-base">{payload.name ?? message.content}</CardTitle>
      </CardHeader>
      {payload.summary ? (
        <CardContent>
          <p className="text-sm text-muted-foreground">{payload.summary}</p>
        </CardContent>
      ) : null}
    </Card>
  );
}
