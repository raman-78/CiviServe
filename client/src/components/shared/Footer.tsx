import { useTranslation } from "react-i18next";
import { Logo } from "@/components/shared/Logo";

export function Footer() {
  const { t } = useTranslation();
  const year = new Date().getFullYear();

  return (
    <footer className="border-t py-6">
      <div className="container flex flex-col items-center justify-between gap-3 px-4 text-center sm:flex-row sm:text-left">
        <Logo className="text-sm" linkToHome={false} />
        <p className="text-xs text-muted-foreground">
          © {year} {t("common.appName")}. {t("footer.tagline")}
        </p>
      </div>
    </footer>
  );
}
