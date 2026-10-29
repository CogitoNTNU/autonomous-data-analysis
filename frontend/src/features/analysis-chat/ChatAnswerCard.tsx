import { AgentTurn } from "@/features/analysis-chat/AgentTurn";
import { AnalysisSummaryTable } from "@/features/analysis-chat/AnalysisSummaryTable";
import { AnalysisChartGallery } from "@/features/analysis-chat/AnalysisChartGallery";
import { agents } from "@/features/analysis-chat/agents";
import { TextList } from "@/features/analysis-chat/TextList";
import type { AnalysisFigure, AnalysisTable, ChatAnswer } from "@/types/planner";

export function ChatAnswerCard({
  answer, figures, tables = [],
}: {
  answer: ChatAnswer;
  figures: AnalysisFigure[];
  tables?: AnalysisTable[];
}) {
  const summary = normalize(answer.text);
  const findings = unique(answer.findings.map((finding) => finding.claim))
    .filter((claim) => normalize(claim) !== summary);
  const notes = unique(answer.limitations);
  return (
    <AgentTurn agent={agents.assistant}>
      <div aria-label="Analysis answer">
        <p className="text-base leading-7">{answer.text}</p>
        <TextList items={findings.slice(0, 3)} title="Key findings" />
        {findings.length > 3 && (
          <details className="mt-3 text-sm text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">More findings ({findings.length - 3})</summary>
            <TextList items={findings.slice(3)} title="Supporting findings" />
          </details>
        )}
        {tables.map((table) => <AnalysisSummaryTable key={table.id} table={table} />)}
        <AnalysisChartGallery figures={figures} figureIds={answer.figureIds} />
        <TextList items={notes} title="Important notes" />
        {answer.followUps.length > 0 && (
          <details className="mt-4 text-sm text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">Follow-up questions</summary>
            <TextList items={unique(answer.followUps)} title="Explore further" />
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
