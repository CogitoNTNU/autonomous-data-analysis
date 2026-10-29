import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents, type AgentIdentity } from "@/features/analysis-chat/agents";

type ThinkingIndicatorProps = {
  agent?: AgentIdentity;
  label?: string;
};

export function ThinkingIndicator({
  agent = agents.planner,
  label,
}: ThinkingIndicatorProps) {
  return (
    <AgentTurn agent={agent} bubble={false}>
      <div aria-live="polite" className="flex min-h-6 flex-wrap items-center gap-x-2.5 gap-y-1" role="status" aria-label={label ?? "Thinking"}>
        {label && <span className="text-sm font-normal leading-6 text-muted-foreground">{label}</span>}
        <div aria-hidden="true" className="flex items-center gap-1.5">
          <span aria-hidden="true" className="thinking-dot" />
          <span aria-hidden="true" className="thinking-dot" />
          <span aria-hidden="true" className="thinking-dot" />
        </div>
      </div>
    </AgentTurn>
  );
}
