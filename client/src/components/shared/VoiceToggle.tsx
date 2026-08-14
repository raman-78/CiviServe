import { Volume2, VolumeX } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSettingsStore } from "@/store/settingsSlice";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/** Voice Assistance on/off. Reads/writes the persisted voiceAssistance preference. */
export function VoiceToggle() {
  const { t } = useTranslation();
  const voiceAssistance = useSettingsStore((s) => s.voiceAssistance);
  const setVoiceAssistance = useSettingsStore((s) => s.setVoiceAssistance);

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            aria-pressed={voiceAssistance}
            aria-label={t("voice.toggle")}
            onClick={() => setVoiceAssistance(!voiceAssistance)}
          >
            {voiceAssistance ? <Volume2 className="h-5 w-5" /> : <VolumeX className="h-5 w-5" />}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          {voiceAssistance ? t("voice.assistanceOn") : t("voice.assistanceOff")}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
