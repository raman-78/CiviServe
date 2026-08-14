import { useTranslation } from "react-i18next";
import { useSettingsStore } from "@/store/settingsSlice";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ttsAdapter } from "@/services/tts";
import type { SpeechSpeed } from "@civiserve/shared";
import { useEffect, useState } from "react";

/** Voice assistance settings: master switch, speed, repeat + preferred voice. */
export function VoiceSettings() {
  const { t } = useTranslation();
  const voiceAssistance = useSettingsStore((s) => s.voiceAssistance);
  const setVoiceAssistance = useSettingsStore((s) => s.setVoiceAssistance);
  const speechSpeed = useSettingsStore((s) => s.speechSpeed);
  const setSpeechSpeed = useSettingsStore((s) => s.setSpeechSpeed);
  const repeatConfirmation = useSettingsStore((s) => s.repeatConfirmation);
  const setRepeatConfirmation = useSettingsStore((s) => s.setRepeatConfirmation);
  const preferredVoice = useSettingsStore((s) => s.preferredVoice);
  const setPreferredVoice = useSettingsStore((s) => s.setPreferredVoice);
  const [voices, setVoices] = useState(ttsAdapter.getVoices());

  // Refresh the voice list when the browser finishes loading voices.
  useEffect(() => {
    const refresh = () => setVoices(ttsAdapter.getVoices());
    const unsub = ttsAdapter.onVoicesChanged(refresh);
    refresh();
    return unsub;
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("settings.voice")}</CardTitle>
        <CardDescription>{t("settings.voiceDesc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label htmlFor="acc-voice">{t("settings.voiceAssistance")}</Label>
            <p className="text-sm text-muted-foreground">{t("settings.voiceAssistanceDesc")}</p>
          </div>
          <Switch
            id="acc-voice"
            checked={voiceAssistance}
            onCheckedChange={setVoiceAssistance}
          />
        </div>

        <Separator />

        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label>{t("settings.speechSpeed")}</Label>
            <p className="text-sm text-muted-foreground">{t("settings.speechSpeedDesc")}</p>
          </div>
          <Select
            value={speechSpeed}
            onValueChange={(value) => setSpeechSpeed(value as SpeechSpeed)}
            defaultValue="normal"
          >
            <SelectTrigger className="w-[130px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="slow">{t("settings.speedSlow")}</SelectItem>
              <SelectItem value="normal">{t("settings.speedNormal")}</SelectItem>
              <SelectItem value="fast">{t("settings.speedFast")}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Separator />

        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label htmlFor="acc-repeat">{t("settings.repeatConfirmation")}</Label>
            <p className="text-sm text-muted-foreground">{t("settings.repeatConfirmationDesc")}</p>
          </div>
          <Switch
            id="acc-repeat"
            checked={repeatConfirmation}
            onCheckedChange={setRepeatConfirmation}
            disabled={!voiceAssistance}
          />
        </div>

        <Separator />

        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <Label>{t("settings.preferredVoice")}</Label>
            <p className="text-sm text-muted-foreground">{t("settings.preferredVoiceDesc")}</p>
          </div>
          <Select
            value={preferredVoice}
            onValueChange={setPreferredVoice}
            defaultValue=""
          >
            <SelectTrigger className="w-[220px]">
              <SelectValue placeholder={t("settings.voiceAutomatic")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">{t("settings.voiceAutomatic")}</SelectItem>
              {voices.map((voice) => (
                <SelectItem key={voice.id} value={voice.id}>
                  {voice.name} ({voice.lang})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}