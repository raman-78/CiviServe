import type { LanguageCode } from "@schemesathi/shared";
import { SpeakerButton } from "@/components/shared/SpeakerButton";

interface SectionSpeakerRowProps {
  id: string;
  title: string;
  /** Plain text this row will read aloud. */
  text: string;
  /** Content language used to pick a voice (defaults to UI language). */
  language?: LanguageCode;
}

/**
 * Section heading with a read-aloud speaker. Used on long-form content
 * (scheme detail sections) so citizens can leaf through a scheme by ear.
 * Speech is user-triggered only.
 */
export function SectionSpeakerRow({ id, title, text, language }: SectionSpeakerRowProps) {
  return (
    <div className="flex items-center justify-between gap-2">
      <h2 className="text-lg font-semibold">{title}</h2>
      <SpeakerButton
        id={`speak-${id}`}
        text={text}
        language={language}
        label="chat.listen"
        size="icon"
        withText={false}
      />
    </div>
  );
}