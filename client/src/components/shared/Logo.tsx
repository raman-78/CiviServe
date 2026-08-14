import { MessageCircleHeart } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  /** Use as a link to "/" when true (default). */
  linkToHome?: boolean;
}

export function Logo({ className, linkToHome = true }: LogoProps) {
  const { t } = useTranslation();
  const content = (
    <span className={cn("flex items-center gap-2", className)}>
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <MessageCircleHeart className="h-5 w-5" />
      </span>
      <span className="font-semibold leading-tight">
        {t("common.appName")}
      </span>
    </span>
  );

  if (!linkToHome) return content;
  return (
    <Link to="/" aria-label={t("common.backHome")}>
      {content}
    </Link>
  );
}
