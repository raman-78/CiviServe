import { useEffect, useRef } from "react";
import { ArrowUp } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useChatStore } from "@/store/chatSlice";
import { useSettingsStore } from "@/store/settingsSlice";
import { MicButton, type MicButtonState } from "@/components/shared/MicButton";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SPEECH_LOCALES } from "@civiserve/shared";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

/** Composer: textarea + real STT mic + send. Transcripts fill the draft for
 *  review — the mic never submits automatically. */
export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const { t } = useTranslation();
  const draftInput = useChatStore((s) => s.draftInput);
  const setDraftInput = useChatStore((s) => s.setDraftInput);
  const uiLanguage = useSettingsStore((s) => s.language);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { supported, status, error, start, stop } = useSpeechRecognition({
    lang: SPEECH_LOCALES[uiLanguage],
    onTranscript: (text) => setDraftInput(text),
  });

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [draftInput]);

  const canSend = draftInput.trim().length > 0 && !disabled;

  const handleSubmit = (event?: React.FormEvent) => {
    event?.preventDefault();
    const text = draftInput.trim();
    if (!text || disabled) return;
    onSend(text);
    setDraftInput("");
    textareaRef.current?.focus();
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  const micState: MicButtonState = !supported
    ? "unsupported"
    : error === "not-allowed"
      ? "denied"
      : status === "listening" || status === "processing"
        ? status
        : "idle";

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 rounded-2xl border bg-background p-2 shadow-sm"
    >
      <MicButton
        className="shrink-0"
        state={micState}
        onStart={start}
        onStop={stop}
        disabled={disabled}
      />
      <Textarea
        ref={textareaRef}
        rows={1}
        value={draftInput}
        onChange={(e) => setDraftInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("chat.placeholder")}
        aria-label={t("chat.placeholder")}
        className="max-h-40 flex-1 resize-none border-0 bg-transparent p-2 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
      />
      <Button
        type="submit"
        size="icon"
        className="shrink-0 rounded-full"
        disabled={!canSend}
        aria-label={t("chat.send")}
      >
        <ArrowUp className="h-4 w-4" />
      </Button>
    </form>
  );
}