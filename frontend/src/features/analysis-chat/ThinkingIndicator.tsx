import { AgentMark } from "@/features/workspace/AgentMark";

export function ThinkingIndicator() {
  return (
    <div
      aria-live="polite"
      className="mt-9 flex gap-4"
      role="status"
    >
      <AgentMark />
      <div className="min-w-0 flex-1 pt-1">
        <div className="flex items-center gap-2">
          <span className="thinking-dot" />
          <span className="thinking-dot" />
          <span className="thinking-dot" />
          <span className="ml-1 text-xs font-medium">Thinking</span>
        </div>
        <div className="mt-3 border-l border-border pl-4 text-[10px] leading-5 text-muted-foreground">
          <p>Reviewing the dataset structure</p>
          <p>Mapping your question to available columns</p>
          <p>Checking whether clarification is needed</p>
        </div>
      </div>
    </div>
  );
}
