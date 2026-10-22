import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import type { PreprocessingReport } from "@/types/planner";

type PreprocessingReportCardProps = {
  report: PreprocessingReport;
};

export function PreprocessingReportCard({ report }: PreprocessingReportCardProps) {
  return (
    <AgentDisclosure agent={agents.preprocessing} summary={summary(report)}>
      <p className="text-xs leading-5">
        {report.rowsBefore} rows in, {report.rowsAfter} rows out.
      </p>
      {report.changes.length > 0 ? (
        <ul className="mt-3 space-y-1.5 text-[11px] leading-4 text-muted-foreground">
          {report.changes.map((change) => (
            <li key={change}>{change}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-[11px] leading-4 text-muted-foreground">
          No rows or columns were changed.
        </p>
      )}
      {report.warnings.length > 0 && (
        <ul className="mt-3 space-y-1 text-[11px] leading-4">
          {report.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
    </AgentDisclosure>
  );
}

function summary(report: PreprocessingReport): string {
  return `Preprocessing finished, ${report.rowsBefore} rows to ${report.rowsAfter}`;
}
