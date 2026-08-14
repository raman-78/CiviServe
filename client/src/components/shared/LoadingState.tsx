import { LoaderCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";

interface LoadingStateProps {
  className?: string;
  /** Optional custom label; defaults to a localized "Loading…". */
  label?: string;
  /** Use a compact inline variant for small containers. */
  compact?: boolean;
}

export function LoadingState({ className, label, compact }: LoadingStateProps) {
  const { t } = useTranslation();

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex w-full flex-col items-center justify-center gap-3 text-muted-foreground",
        compact ? "py-6" : "py-16",
        className,
      )}
    >
      <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
      <p className="text-sm">{label ?? t("common.loading")}</p>
    </div>
  );
}
