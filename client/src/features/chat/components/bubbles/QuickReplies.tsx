import { useTranslation } from "react-i18next";
import type { ChatMessage, QuickReply } from "@/types";
import { Button } from "@/components/ui/button";

interface QuickRepliesProps {
  message: ChatMessage;
  onPick?: (reply: QuickReply) => void;
}

/** Suggested reply chips rendered under an assistant message. */
export function QuickReplies({ message, onPick }: QuickRepliesProps) {
  const { t } = useTranslation();
  const payload = (message.payload ?? {}) as {
    replies?: QuickReply[];
  };

  const replies = payload.replies ?? [];

  if (replies.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label={t("chat.suggested")}>
      {replies.map((reply, index) => (
        <Button
          key={index}
          type="button"
          variant="outline"
          size="sm"
          className="rounded-full"
          onClick={() => onPick?.(reply)}
        >
          {reply.label}
        </Button>
      ))}
    </div>
  );
}
