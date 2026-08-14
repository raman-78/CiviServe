import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

/** 404 fallback rendered within the current layout. */
export function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-6xl font-bold text-muted-foreground">404</p>
      <h1 className="mt-4 text-2xl font-semibold">{t("nav.home")}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{t("common.backHome")}</p>
      <Button asChild className="mt-6">
        <Link to="/">{t("common.backHome")}</Link>
      </Button>
    </div>
  );
}
