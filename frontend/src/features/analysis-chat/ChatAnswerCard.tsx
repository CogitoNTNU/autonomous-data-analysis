import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { AnalysisSummaryTable } from "@/features/analysis-chat/AnalysisSummaryTable";
import { AnalysisChartGallery } from "@/features/analysis-chat/AnalysisChartGallery";
import { agents } from "@/features/analysis-chat/agents";
import { FollowUpQuestions } from "@/features/analysis-chat/FollowUpQuestions";
import { TextList } from "@/features/analysis-chat/TextList";
import { MarkdownText } from "@/features/analysis-chat/MarkdownText";
import { ImportantNotes } from "@/features/analysis-chat/ImportantNotes";
import type { AnalysisFigure, AnalysisTable, ChatAnswer } from "@/types/planner";

const fallbackFollowUps = [
  "Explain the most important finding",
  "Which limitations matter most?",
  "What should I analyze next?",
];

export function ChatAnswerCard({
  answer, figures, tables = [], onFollowUp,
}: {
  answer: ChatAnswer;
  figures: AnalysisFigure[];
  tables?: AnalysisTable[];
  onFollowUp?: (question: string) => void;
}) {
  const summary = normalize(answer.text);
  const findings = unique(answer.findings.map((finding) => finding.claim))
    .filter((claim) => normalize(claim) !== summary);
  const followUps = unique(answer.followUps);
  const availableFollowUps = followUps.length > 0 ? followUps : fallbackFollowUps;
  return (
    <AgentTurn agent={agents.assistant}>
      <div aria-label="Analysis answer">
        <MarkdownText text={answer.text} />
        <TextList items={findings.slice(0, 3)} title="Key findings" />
        {findings.length > 3 && (
          <details className="mt-3 text-sm text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">More findings ({findings.length - 3})</summary>
            <TextList items={findings.slice(3)} title="Supporting findings" />
          </details>
        )}
        {tables.map((table) => <AnalysisSummaryTable key={table.id} table={table} />)}
        <AnalysisChartGallery figures={figures} figureIds={answer.figureIds} />
        <ImportantNotes limitations={answer.limitations} />
        {onFollowUp ? (
          <FollowUpQuestions questions={availableFollowUps} onSelect={onFollowUp} />
        ) : followUps.length > 0 && (
          <details className="mt-4 text-sm text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">Follow-up questions</summary>
            <TextList items={followUps} title="Explore further" />
          </details>
        )}
      </div>
    </AgentTurn>
  );
}

function normalize(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

function unique(values: string[]): string[] {
  const seen = new Set<string>();
  return values.filter((value) => {
    const key = normalize(value);
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
