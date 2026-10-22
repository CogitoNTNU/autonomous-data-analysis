import { useState, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";

import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import type { AgentIdentity } from "@/features/analysis-chat/agents";
import { cn } from "@/lib/utils";

type AgentDisclosureProps = {
  agent: AgentIdentity;
  summary: string;
  children: ReactNode;
  actions?: ReactNode;
};

export function AgentDisclosure({
  agent,
  summary,
  children,
  actions,
}: AgentDisclosureProps) {
  const [open, setOpen] = useState(false);
  const detailsId = `${agent.initials.toLowerCase()}-details`;

  return (
    <section>
      <AgentTurn agent={agent}>
        <button
          aria-controls={detailsId}
          aria-expanded={open}
          className="flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-left text-xs"
          onClick={() => setOpen((current) => !current)}
          type="button"
        >
          <span className="min-w-0 flex-1">{summary}</span>
          <ChevronRight
            className={cn(
              "size-3.5 shrink-0 text-muted-foreground transition-transform",
              open && "rotate-90",
            )}
          />
        </button>
        {actions}
        {open && (
          <div className="mt-3" id={detailsId}>
            {children}
          </div>
        )}
      </AgentTurn>
    </section>
  );
}
