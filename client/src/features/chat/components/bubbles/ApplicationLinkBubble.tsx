import { ExternalLink, Phone } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import type { ChatMessage } from "@/types";

interface ApplicationLinks {
  online?: string;
  offline?: string;
  helpline?: string;
}

/** Application guidance card with online/offline/helpline actions. */
export function ApplicationLinkBubble({ message }: { message: ChatMessage }) {
  const { t } = useTranslation();
  const payload = (message.payload ?? {}) as {
    links?: ApplicationLinks;
  };

  const links = payload.links ?? {};

  return (
    <div className="w-full max-w-md rounded-2xl rounded-bl-sm border bg-background p-4">
      <p className="text-sm">{message.renderedText ?? message.content}</p>
      {links.offline ? <p className="mt-2 text-xs text-muted-foreground">{links.offline}</p> : null}
      <div className="mt-3 flex flex-wrap gap-2">
        {links.online ? (
          <Button size="sm" asChild>
            <a href={links.online} target="_blank" rel="noreferrer">
              {t("common.officialLink")}
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </Button>
        ) : null}
        {links.helpline ? (
          <Button size="sm" variant="outline" asChild>
            <a href={`tel:${links.helpline}`}>
              <Phone className="h-3.5 w-3.5" />
              {links.helpline}
            </a>
          </Button>
        ) : null}
      </div>
    </div>
  );
}
