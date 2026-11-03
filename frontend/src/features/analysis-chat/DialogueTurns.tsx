import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { agents } from "@/features/analysis-chat/agents";
import { UserMessage } from "@/features/analysis-chat/UserMessage";
import type { DialogueTurn } from "@/types/dialogue";

export function DialogueTurns({ turns }: { turns: DialogueTurn[] }) {
  return turns.map((turn, index) => turn.role === "user" ? (
    <UserMessage key={index} text={turn.content} />
  ) : (
    <AgentTurn key={index} agent={agents.assistant}>
      {turn.failed ? (
        <p className="text-base leading-7 text-destructive" role="alert">{turn.content}</p>
      ) : (
        <p className="whitespace-pre-line text-base leading-7">{turn.content}</p>
      )}
      {turn.startsAnalysis && !turn.failed && (
        <p className="mt-2 text-sm text-muted-foreground">New analysis requested</p>
      )}
    </AgentTurn>
  ));
}
