import { cn } from "@/lib/utils";

/** Three-dot "Sathi is typing…" indicator for in-flight assistant turns. */
export function TypewriterBubble({ className }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="typing"
      className={cn(
        "grid grid-cols-3 gap-1.5 rounded-2xl rounded-bl-sm bg-muted px-4 py-3",
        className,
      )}
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </div>
  );
}