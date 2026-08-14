import { Mic, MicOff, LoaderCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type MicButtonState = "idle" | "listening" | "processing" | "denied" | "unsupported";

interface MicButtonProps {
  state: MicButtonState;
  onStart?: () => void;
  onStop?: () => void;
  disabled?: boolean;
  className?: string;
}

/**
 * STT mic button wired to the SpeechToTextAdapter. Visual states mirror the
 * recognition lifecycle (idle / listening / processing) plus the two failure
 * modes (denied + unsupported). Clicking while listening stops the mic.
 */
export function MicButton({ state, onStart, onStop, disabled, className }: MicButtonProps) {
  const { t } = useTranslation();

  const listening = state === "listening" || state === "processing";
  const denied = state === "denied";
  const unsupported = state === "unsupported";

  const handleClick = () => {
    if (listening) {
      onStop?.();
      return;
    }
    if (!denied && !unsupported) onStart?.();
  };

  const label = unsupported
    ? t("voice.unsupported")
    : denied
      ? t("voice.denied")
      : listening
        ? t("voice.stopRecording")
        : t("voice.startRecording");

  return (
    <Button
      type="button"
      variant={listening ? "destructive" : "ghost"}
      size="icon"
      className={cn(listening && "animate-pulse", className)}
      aria-label={label}
      title={label}
      disabled={disabled || unsupported}
      onClick={handleClick}
    >
      {listening ? (
        <LoaderCircle className="h-5 w-5 animate-spin" />
      ) : denied || unsupported ? (
        <MicOff className="h-5 w-5 text-muted-foreground" />
      ) : (
        <Mic className="h-5 w-5" />
      )}
    </Button>
  );
}