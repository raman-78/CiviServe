import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  /** @deprecated use `description` — both are supported for now. */
  subtitle?: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

/** Consistent page heading block (title + description + optional actions). */
export function PageHeader({
  title,
  subtitle,
  description,
  actions,
  className,
}: PageHeaderProps) {
  const body = description ?? subtitle;
  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between",
        className,
      )}
    >
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {body ? (
          <p className="max-w-2xl text-sm text-muted-foreground">{body}</p>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}
