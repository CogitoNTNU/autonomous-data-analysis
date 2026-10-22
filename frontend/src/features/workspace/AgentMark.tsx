import { cn } from "@/lib/utils";

type AgentMarkProps = {
  compact?: boolean;
  className?: string;
  initials?: string;
};

export function AgentMark({
  compact = false,
  className,
  initials = "DA",
}: AgentMarkProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "grid shrink-0 place-items-center rounded-full bg-foreground font-semibold text-background",
        compact ? "size-7 text-[10px]" : "size-8 text-xs",
        className,
      )}
    >
      {initials}
    </div>
  );
}
