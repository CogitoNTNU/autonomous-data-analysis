import type { ReactNode } from "react";

import { AgentMark } from "@/features/workspace/AgentMark";

import type { AgentIdentity } from "@/features/analysis-chat/agents";

type AgentTurnProps = {
  agent: AgentIdentity;
  children: ReactNode;
};

export function AgentTurn({ agent, children }: AgentTurnProps) {
  return (
    <div className="mt-9 flex gap-4">
      <AgentMark initials={agent.initials} />
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-semibold">{agent.name}</p>
        {children}
      </div>
    </div>
  );
}
