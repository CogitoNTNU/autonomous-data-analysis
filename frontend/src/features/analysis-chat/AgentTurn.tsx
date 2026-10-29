import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { AgentMark } from "@/features/workspace/AgentMark";
import type { AgentIdentity } from "@/features/analysis-chat/agents";

type AgentTurnProps = {
  agent: AgentIdentity;
  children: ReactNode;
  bubble?: boolean;
  compact?: boolean;
};

export function AgentTurn({ agent, children, bubble = true, compact = false }: AgentTurnProps) {
  return (
    <div className={cn("relative", compact ? "mt-4" : "mt-8 sm:mt-10")}>
      <div className="mb-3 sm:absolute sm:right-full sm:top-0 sm:mb-0 sm:mr-4">
        <AgentMark initials={agent.initials} />
      </div>
      <div className="min-w-0 w-full">
        <div className="flex min-h-9 items-center gap-3">
          <p className="text-lg font-semibold leading-7 tracking-tight">{agent.name}</p>
        </div>
        {!bubble && <div className="mt-1">{children}</div>}
        {bubble && (
          <div className={cn(
            "border border-border bg-muted/40",
            compact ? "mt-1 rounded-2xl px-4 py-2.5" : "mt-2 rounded-3xl px-4 py-4 sm:px-5",
            "rounded-tl-md",
          )}>
            {children}
          </div>
        )}
      </div>
    </div>
  );
}
