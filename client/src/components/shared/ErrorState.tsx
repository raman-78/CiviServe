import { AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  className?: string;
  title?: string;
  /** Human-readable error detail (already normalized, never raw errors). */
  message?: string;
  /** Optional action callback; defaults to a retry button. */
  onRetry?: () => void;
}

/** Uniform async-failure fallback (docs/architecture/13). */
export function ErrorState({ className, title, message, onRetry }: ErrorStateProps) {
  const { t } = useTranslation();

  return (
    <div
      role="alert"
      className={cn(
        "flex w-full flex-col items-center justify-center gap-3 py-16 text-center",
        className,
      )}
    >
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="h-6 w-6 text-destructive" />
      </span>
      <div className="space-y-1">
        <p className="font-medium">{title ?? t("error.title")}</p>
        {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
      </div>
      <div className="flex gap-2">
        {onRetry ? (
          <Button variant="outline" size="sm" onClick={onRetry}>
            {t("common.retry")}
          </Button>
        ) : null}
        <Button variant="ghost" size="sm" asChild>
          <Link to="/">{t("common.backHome")}</Link>
        </Button>
      </div>
    </div>
  );
}
