import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  BookOpenCheck,
  HeartHandshake,
  Languages,
  Mic,
  MapPinned,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const FEATURES = [
  { key: "chat", icon: Languages },
  { key: "eligibility", icon: BookOpenCheck },
  { key: "voice", icon: Mic },
  { key: "centers", icon: MapPinned },
] as const;

export function LandingPage() {
  const { t } = useTranslation();

  return (
    <div className="container px-4 py-16">
      <section className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          {t("landing.heroTitle")}
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">{t("landing.heroSubtitle")}</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button size="lg" asChild>
            <Link to="/chat">{t("landing.startChat")}</Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link to="/schemes">{t("landing.browseSchemes")}</Link>
          </Button>
        </div>
      </section>

      <section className="mt-20">
        <h2 className="mb-6 text-center text-2xl font-semibold">
          {t("landing.featuresTitle")}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ key, icon: Icon }) => (
            <Card key={key}>
              <CardHeader className="items-center text-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                  <Icon className="h-6 w-6 text-primary" />
                </span>
                <CardTitle className="text-base">{t(`landing.feature${key[0].toUpperCase()}${key.slice(1)}`)}</CardTitle>
                <CardDescription>
                  {t(`landing.feature${key[0].toUpperCase()}${key.slice(1)}Desc`)}
                </CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      <section className="mt-20 rounded-2xl bg-primary/5 p-8 text-center">
        <HeartHandshake className="mx-auto h-10 w-10 text-primary" />
        <h2 className="mt-4 text-2xl font-semibold">{t("common.tagline")}</h2>
      </section>
    </div>
  );
}
