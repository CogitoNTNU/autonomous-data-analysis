import { Button } from "@/components/ui/button";
import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents } from "@/features/analysis-chat/agents";
import type {
  ClarificationOption,
  ClarificationRequest,
} from "@/types/planner";

type ClarificationPromptProps = {
  awaitingCustomAnswer?: boolean;
  clarification: ClarificationRequest;
  onSelect: (option: ClarificationOption) => void;
};

export function ClarificationPrompt({
  awaitingCustomAnswer = false,
  clarification,
  onSelect,
}: ClarificationPromptProps) {
  return (
    <section aria-labelledby="clarification-question">
      <AgentTurn agent={agents.planner}>
        <h2 className="text-[13px] font-medium" id="clarification-question">
          {clarification.question}
        </h2>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          {clarification.description}
        </p>
        {awaitingCustomAnswer ? (
          <p className="mt-4 rounded-xl border border-border bg-muted/50 px-3 py-2 text-[10px] text-muted-foreground">
            Explain what you mean in the message field below.
          </p>
        ) : (
          <div className="mt-4 flex flex-wrap gap-2">
            {clarification.options.map((option) => (
              <Button
                key={option.id}
                onClick={() => onSelect(option)}
                size="sm"
                type="button"
                variant="outline"
              >
                {option.label}
              </Button>
            ))}
          </div>
        )}
      </AgentTurn>
    </section>
  );
}
