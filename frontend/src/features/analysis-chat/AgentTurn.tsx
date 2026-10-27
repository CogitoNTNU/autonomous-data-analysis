import type { ReactNode } from "react";

import { AgentMark } from "@/features/workspace/AgentMark";
import type { AgentIdentity } from "@/features/analysis-chat/agents";

type AgentTurnProps = {
  agent: AgentIdentity;
  children: ReactNode;
  bubble?: boolean;
};

export function AgentTurn({ agent, children, bubble = true }: AgentTurnProps) {
  return (
    <div className="relative mt-8 sm:mt-10">
      <div className="mb-2 sm:absolute sm:right-full sm:top-0 sm:mb-0 sm:mr-4">
        <AgentMark initials={agent.initials} />
      </div>
      <div className="min-w-0 w-full">
        <div className="flex min-h-8 items-center gap-3">
          <p className="text-base font-semibold">{agent.name}</p>
          {!bubble && children}
        </div>
        {bubble && (
          <div className="mt-2 rounded-3xl rounded-tl-md border border-border bg-muted/40 px-4 py-4 sm:px-5">
            {children}
          </div>
        )}
      </div>
    </div>
  );
}
