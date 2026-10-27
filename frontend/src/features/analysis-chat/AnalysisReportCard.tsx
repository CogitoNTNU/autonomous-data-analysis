import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import { WarningList } from "@/features/analysis-chat/WarningList";
import type { AnalysisReport } from "@/types/planner";

export function AnalysisReportCard({ analysis }: { analysis: AnalysisReport }) {
  const count = analysis.steps.length;
  const label = count === 1 ? "result" : "results";
  return (
    <AgentDisclosure
      agent={agents.analysis}
      summary={`Analysis finished, ${count} ${label}`}
    >
      {analysis.steps.length > 0 ? (
        <ul className="space-y-3">
          {analysis.steps.map((step) => (
            <li key={step.id}>
              <p className="text-xs font-semibold">{title(step.method)}</p>
              <p className="mt-1 text-[11px] leading-4 text-muted-foreground">
                {step.detail}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[11px] leading-4 text-muted-foreground">
          No analysis steps were run.
        </p>
      )}
      {analysis.figures.map((figure) => (
        <img
          alt="Analysis chart"
          className="mt-3 max-w-full rounded-lg border border-border"
          key={figure.id}
          src={figure.image}
        />
      ))}
      <WarningList warnings={analysis.warnings} />
    </AgentDisclosure>
  );
}

function title(method: string): string {
  return method.replaceAll("_", " ");
}
