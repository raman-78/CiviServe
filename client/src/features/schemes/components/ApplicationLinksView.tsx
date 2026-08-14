import { ExternalLink, MapPin, Phone } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { SchemeApplicationLinks } from "@/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SpeakerButton } from "@/components/shared/SpeakerButton";

interface ApplicationLinksViewProps {
  links: SchemeApplicationLinks;
}

/** How-to-apply card: online portal, offline path and helpline. */
export function ApplicationLinksView({ links }: ApplicationLinksViewProps) {
  const { t } = useTranslation();

  const speechText = [links.online, links.offline, links.helpline]
    .filter(Boolean)
    .join(". ");

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-lg">{t("schemes.howToApply")}</CardTitle>
          <SpeakerButton
            id="speak-how-to-apply"
            text={speechText}
            language="en"
            label="chat.listen"
            size="icon"
          />
        </div>
        <CardDescription>
          {links.offline ?? t("common.officialLink")}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        {links.online ? (
          <Button asChild>
            <a href={links.online} target="_blank" rel="noreferrer">
              {t("common.officialLink")}
              <ExternalLink className="h-4 w-4" />
            </a>
          </Button>
        ) : null}
        {links.helpline ? (
          <Button variant="outline" asChild>
            <a href={`tel:${links.helpline}`}>
              <Phone className="h-4 w-4" />
              {links.helpline}
            </a>
          </Button>
        ) : null}
        {links.sourceUrl ? (
          <Button variant="ghost" asChild>
            <a href={links.sourceUrl} target="_blank" rel="noreferrer">
              <MapPin className="h-4 w-4" />
              {t("schemes.lastVerified")}
            </a>
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
