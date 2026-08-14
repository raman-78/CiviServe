import { useTranslation } from "react-i18next";
import { PageHeader } from "@/components/shared/PageHeader";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const FAQS = [
  {
    id: "what",
    q: "What is CiviServe?",
    a: "CiviServe helps you discover and understand central and state government schemes, in your own language.",
  },
  {
    id: "free",
    q: "Is it free?",
    a: "Yes. CiviServe is a free public service.",
  },
  {
    id: "private",
    q: "Is my information private?",
    a: "We only use the minimum profile you choose to share, to recommend schemes you may qualify for.",
  },
  {
    id: "voice",
    q: "Can I speak to the assistant?",
    a: "Yes — use the microphone to ask, and the speaker button to hear any reply read aloud in your language. Nothing is ever read without your say-so.",
  },
];

/** Help/FAQ page (static content). */
export function HelpPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <PageHeader title={t("help.title")} subtitle={t("help.subtitle")} />
      <Accordion type="single" collapsible className="w-full max-w-2xl">
        {FAQS.map((faq) => (
          <AccordionItem key={faq.id} value={faq.id}>
            <AccordionTrigger>{faq.q}</AccordionTrigger>
            <AccordionContent>{faq.a}</AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
