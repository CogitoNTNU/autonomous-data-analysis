import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import { TextList } from "@/features/analysis-chat/TextList";
import type { ChatAnswer } from "@/types/planner";

export function ChatAnswerCard({ answer }: { answer: ChatAnswer }) {
  return (
    <AgentDisclosure agent={agents.chat} summary="Prepared an answer">
      <p className="text-xs leading-5">{answer.text}</p>
      <TextList items={answer.followUps} title="Follow-up questions" />
    </AgentDisclosure>
  );
}
