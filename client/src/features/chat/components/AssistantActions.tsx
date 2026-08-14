import { useTranslation } from "react-i18next";
import { Check, RefreshCw, RotateCcw } from "lucide-react";
import { useState } from "react";
import type { ChatMessage } from "@/types";
import { Button } from "@/components/ui/button";
import { SpeakerButton } from "@/components/shared/SpeakerButton";

interface AssistantActionsProps {
  message: ChatMessage;
  onRegenerate?: (message: ChatMessage) => void;
  onRetry?: (message: ChatMessage) => void;
}

/** Action bar under assistant messages: speak / copy / regenerate / retry. */
export function AssistantActions({ message, onRegenerate, onRetry }: AssistantActionsProps) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const text = message.renderedText ?? message.content;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard unavailable (non-HTTPS / permissions) — ignore.
    }
  };

  return (
    <div className="mt-1.5 flex items-center gap-1">
      {text ? (
        <SpeakerButton
          id={`speak-message-${message.id}`}
          text={text}
          language={message.language}
          label="chat.listen"
          size="sm"
        />
      ) : null}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-6 gap-1 px-1.5 text-xs text-muted-foreground"
        onClick={handleCopy}
      >
        {copied ? <Check className="h-3 w-3" /> : <CopyIcon className="h-3 w-3" />}
        {copied ? t("chat.copied") : t("chat.copy")}
      </Button>
      {message.status === "failed" ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-6 gap-1 px-1.5 text-xs text-muted-foreground"
          onClick={() => onRetry?.(message)}
        >
          <RotateCcw className="h-3 w-3" />
          {t("chat.retry")}
        </Button>
      ) : (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-6 gap-1 px-1.5 text-xs text-muted-foreground"
          onClick={() => onRegenerate?.(message)}
        >
          <RefreshCw className="h-3 w-3" />
          {t("chat.regenerate")}
        </Button>
      )}
    </div>
  );
}

function CopyIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}