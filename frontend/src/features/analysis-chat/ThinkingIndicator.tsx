import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents, type AgentIdentity } from "@/features/analysis-chat/agents";

type ThinkingIndicatorProps = {
  agent?: AgentIdentity;
};

export function ThinkingIndicator({
  agent = agents.planner,
}: ThinkingIndicatorProps) {
  return (
    <AgentTurn agent={agent} bubble={false}>
      <div aria-live="polite" className="flex h-3 items-center" role="status" aria-label="Thinking">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="thinking-dot" />
          <span aria-hidden="true" className="thinking-dot" />
          <span aria-hidden="true" className="thinking-dot" />
        </div>
      </div>
    </AgentTurn>
  );
}
