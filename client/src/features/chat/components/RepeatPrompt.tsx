import { useState } from "react";
import { Volume2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { ChatMessage } from "@/types";
import { useSettingsStore } from "@/store/settingsSlice";
import { useSpeaker } from "@/hooks/useSpeaker";
import { Button } from "@/components/ui/button";
import { SPEECH_LOCALES, SPEECH_RATES } from "@schemesathi/shared";

interface RepeatPromptProps {
  message: ChatMessage;
}

/**
 * Post-reply "Would you like me to read this aloud?" prompt. Visible ONLY while
 * Voice Assistance is ON and repeat-confirmations are enabled — replies are
 * never read automatically. The answer is remembered for the session per
 * message, so answering once hides the prompt for that message.
 */
export function RepeatPrompt({ message }: RepeatPromptProps) {
  const { t } = useTranslation();
  const voiceAssistance = useSettingsStore((s) => s.voiceAssistance);
  const repeatConfirmation = useSettingsStore((s) => s.repeatConfirmation);
  const speechSpeed = useSettingsStore((s) => s.speechSpeed);
  const slowSpeech = useSettingsStore((s) => s.slowSpeech);
  const { speak, supported } = useSpeaker(`repeat-${message.id}`);

  const [answered, setAnswered] = useState(false);

  const text = message.renderedText ?? message.content;
  if (
    !supported ||
    !voiceAssistance ||
    !repeatConfirmation ||
    answered ||
    !text.trim()
  ) {
    return null;
  }

  const rate = slowSpeech ? SPEECH_RATES.slow : SPEECH_RATES[speechSpeed];

  const handleYes = () => {
    setAnswered(true);
    speak(text, {
      lang: SPEECH_LOCALES[message.language ?? "en"],
      rate,
    });
  };

  const handleNo = () => setAnswered(true);

  return (
    <div
      className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground"
      data-testid="repeat-prompt"
    >
      <span>{t("voice.repeatPrompt")}</span>
      <div className="flex items-center gap-1">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 gap-1 px-2 text-xs"
          onClick={handleYes}
        >
          <Volume2 className="h-3.5 w-3.5" />
          {t("voice.readYes")}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={handleNo}
        >
          {t("voice.readNo")}
        </Button>
      </div>
    </div>
  );
}