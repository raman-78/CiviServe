import { MapPin } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { ChatMessage } from "@/types";
import { formatDistanceKm } from "@/lib/formatters";

interface CenterItem {
  name?: string;
  address?: string;
  distanceKm?: number;
}

/** Nearby service-centre results as a conversation card. */
export function CenterListBubble({ message }: { message: ChatMessage }) {
  const payload = (message.payload ?? {}) as {
    centers?: CenterItem[];
  };

  const centers = payload.centers ?? [];

  if (centers.length === 0) {
    return (
      <div className="w-full max-w-md rounded-2xl rounded-bl-sm border bg-background px-4 py-3 text-sm text-muted-foreground">
        {message.renderedText ?? message.content}
      </div>
    );
  }

  return (
    <div className="w-full max-w-md space-y-2">
      {centers.map((center, index) => (
        <Card key={index} className="flex items-start gap-3 px-4 py-3">
          <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <div className="min-w-0 space-y-0.5">
            <p className="text-sm font-medium">{center.name}</p>
            {center.address ? (
              <p className="text-xs text-muted-foreground">{center.address}</p>
            ) : null}
            {center.distanceKm !== undefined ? (
              <p className="text-xs text-primary">{formatDistanceKm(center.distanceKm)}</p>
            ) : null}
          </div>
        </Card>
      ))}
    </div>
  );
}
