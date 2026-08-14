import { Volume2, VolumeX } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSpeaker } from "@/hooks/useSpeaker";
import { useSettingsStore } from "@/store/settingsSlice";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { SPEECH_LOCALES, SPEECH_RATES } from "@schemesathi/shared";
import type { LanguageCode } from "@schemesathi/shared";

interface SpeakerButtonProps {
  /** Stable unique id for this button (drives the single-speaker state). */
  id: string;
  /** Text to read aloud. */
  text: string;
  /** Message/page language used to pick a voice. Defaults to the UI language. */
  language?: LanguageCode;
  /** i18n base label, e.g. "chat.listen". Speak/Stop labels derive from it. */
  label?: string;
  className?: string;
  variant?: "ghost" | "outline" | "default";
  /** Show a text word next to the icon (small buttons). */
  withText?: boolean;
  size?: "default" | "sm" | "icon";
}

/**
 * User-triggered speaker button (never speaks automatically). Reads the current
 * UI language + persisted speed/voice from the settings store and plays via the
 * shared TTS adapter (one-at-a-time app-wide).
 */
export function SpeakerButton({
  id,
  text,
  language,
  label = "chat.listen",
  className,
  variant = "ghost",
  withText = false,
  size = "sm",
}: SpeakerButtonProps) {
  const { t } = useTranslation();
  const uiLanguage = useSettingsStore((s) => s.language);
  const speechSpeed = useSettingsStore((s) => s.speechSpeed);
  const preferredVoice = useSettingsStore((s) => s.preferredVoice);
  const { speaking, speak, stop, supported } = useSpeaker(id);

  if (!supported) return null;

  const lang = SPEECH_LOCALES[language ?? uiLanguage];

  const handleClick = () => {
    if (speaking) {
      stop("this");
      return;
    }
    speak(text, { lang, rate: SPEECH_RATES[speechSpeed], voiceId: preferredVoice });
  };

  return (
    <Button
      type="button"
      variant={variant}
      size={size}
      className={cn("gap-1 text-muted-foreground", speaking && "text-foreground", className)}
      aria-label={speaking ? t("chat.stopListening") : t(label)}
      onClick={handleClick}
    >
      {speaking ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
      {withText ? <span className="text-xs">{speaking ? t("chat.stopListening") : t(label)}</span> : null}
    </Button>
  );
}