import { useTranslation } from "react-i18next";
import { BadgeCheck, ExternalLink, Info } from "lucide-react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type {
  AssistantChatPayload,
  ChatMessage,
  SchemeReference,
} from "@/types";

interface AssistantRichExtrasProps {
  message: ChatMessage;
  onPickQuestion?: (text: string) => void;
}

/**
 * Structured extras rendered under a plain assistant reply: referenced scheme
 * cards, rule-based recommendations, and follow-up question chips.
 */
export function AssistantRichExtras({ message, onPickQuestion }: AssistantRichExtrasProps) {
  const { t } = useTranslation();
  const payload = (message.payload ?? {}) as Partial<AssistantChatPayload>;
  const grounding = payload.grounding;
  const schemes = payload.referencedSchemes ?? [];
  const recommendations = payload.recommendations ?? [];
  const followUps = payload.followUpQuestions ?? [];

  const content = message.renderedText ?? message.content;

  return (
    <div className="mt-3 space-y-3">
      {schemes.length > 0 && (
        <div className="space-y-2">
          {schemes.slice(0, 3).map((scheme) => (
            <SchemeReferenceCard key={scheme.code} scheme={scheme} />
          ))}
        </div>
      )}

      {recommendations.length > 0 && (
        <div className="rounded-lg border bg-background/60 p-3">
          <p className="mb-2 text-xs font-medium text-muted-foreground">
            {t("chat.recommendations")}
          </p>
          <ul className="space-y-1.5">
            {recommendations.slice(0, 3).map((rec) => (
              <li key={rec.code} className="flex items-start gap-2 text-sm">
                <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                <span>
                  <span className="font-medium">{rec.name ?? rec.code}</span>
                  {rec.reason ? (
                    <span className="text-muted-foreground"> — {rec.reason}</span>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {followUps.length > 0 && (
        <div className="flex flex-wrap gap-2" role="group" aria-label={t("chat.suggested")}>
          {followUps.map((question, index) => (
            <Button
              key={`${index}-${question}`}
              type="button"
              variant="outline"
              size="sm"
              className="rounded-full"
              onClick={() => onPickQuestion?.(question)}
            >
              {question}
            </Button>
          ))}
        </div>
      )}

      {grounding ? (
        <p
          className={`flex items-start gap-1.5 text-xs ${
            grounding.verified ? "text-muted-foreground" : "text-amber-600"
          }`}
        >
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {content.includes("could not be verified")
            ? grounding.note
            : t("chat.grounded", { count: grounding.sources.length })}
        </p>
      ) : null}
    </div>
  );
}

function SchemeReferenceCard({ scheme }: { scheme: SchemeReference }) {
  const { t } = useTranslation();
  return (
    <Card className="w-full max-w-md">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          {scheme.category ? <Badge variant="secondary">{scheme.category}</Badge> : null}
          {scheme.code ? (
            <span className="text-xs text-muted-foreground">{scheme.code}</span>
          ) : null}
        </div>
        <CardTitle className="text-base">{scheme.name}</CardTitle>
      </CardHeader>
      {scheme.summary ? (
        <CardContent>
          <p className="text-sm text-muted-foreground">{scheme.summary}</p>
        </CardContent>
      ) : null}
      {scheme.officialWebsite ? (
        <CardFooter className="pt-0">
          <a
            href={scheme.officialWebsite}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
          >
            <ExternalLink className="h-3 w-3" />
            {t("common.officialLink")}
          </a>
        </CardFooter>
      ) : null}
    </Card>
  );
}