import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents, type AgentIdentity } from "@/features/analysis-chat/agents";

const plannerDetail = [
  "Reviewing the dataset structure",
  "Mapping your question to available columns",
  "Checking whether clarification is needed",
];

type ThinkingIndicatorProps = {
  agent?: AgentIdentity;
  detail?: string[];
};

export function ThinkingIndicator({
  agent = agents.planner,
  detail = plannerDetail,
}: ThinkingIndicatorProps) {
  return (
    <AgentTurn agent={agent}>
      <div aria-live="polite" className="pt-1" role="status">
        <div className="flex items-center gap-2">
          <span className="thinking-dot" />
          <span className="thinking-dot" />
          <span className="thinking-dot" />
          <span className="ml-1 text-xs font-medium">Thinking</span>
        </div>
        <div className="mt-3 border-l border-border pl-4 text-[10px] leading-5 text-muted-foreground">
          {detail.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      </div>
    </AgentTurn>
  );
}
