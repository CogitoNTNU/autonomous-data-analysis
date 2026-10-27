import type { ReactNode } from "react";
import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import type {
  AnalysisReport,
  ChatAnswer,
  CritiqueView,
  InterpretationView,
} from "@/types/planner";

export function AnalysisReportCard({ analysis, actions }: { analysis: AnalysisReport; actions?: ReactNode }) {
  const count = analysis.steps.length;
  const label = count === 1 ? "result" : "results";
  return (
    <AgentDisclosure
      actions={actions}
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

export function InterpretationCard({
  interpretation,
  actions,
}: {
  interpretation: InterpretationView;
  actions?: ReactNode;
}) {
  return (
    <AgentDisclosure actions={actions} agent={agents.interpretation} summary="Interpretation finished">
      <p className="text-xs leading-5">{interpretation.summary}</p>
      <TextList items={interpretation.findings} title="Findings" />
      <TextList items={interpretation.limitations} title="Limitations" />
    </AgentDisclosure>
  );
}

export function CriticCard({ critique, actions }: { critique: CritiqueView; actions?: ReactNode }) {
  return (
    <AgentDisclosure actions={actions} agent={agents.critic} summary={criticSummary(critique.decision)}>
      {critique.issues.length > 0 ? (
        <ul className="space-y-1.5 text-[11px] leading-4 text-muted-foreground">
          {critique.issues.map((issue) => (
            <li key={issue}>{issue}</li>
          ))}
        </ul>
      ) : (
        <p className="text-[11px] leading-4 text-muted-foreground">
          No issues were raised.
        </p>
      )}
      <TextList items={critique.requiredChanges} title="Required changes" />
    </AgentDisclosure>
  );
}

export function ChatAnswerCard({ answer }: { answer: ChatAnswer }) {
  return (
    <AgentDisclosure agent={agents.chat} summary="Prepared an answer">
      <p className="text-xs leading-5">{answer.text}</p>
      <TextList items={answer.followUps} title="Follow-up questions" />
    </AgentDisclosure>
  );
}

function criticSummary(decision: CritiqueView["decision"]): string {
  if (decision === "approved") {
    return "Critic approved";
  }
  if (decision === "revise") {
    return "Critic asked for a revision";
  }
  return "Critic could not complete the review";
}

function title(method: string): string {
  return method.replaceAll("_", " ");
}

function TextList({ items, title: heading }: { items: string[]; title: string }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="mt-3">
      <p className="text-[10px] font-semibold">{heading}</p>
      <ul className="mt-1.5 space-y-1.5 text-[11px] leading-4 text-muted-foreground">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function WarningList({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) {
    return null;
  }
  return (
    <ul className="mt-3 space-y-1 text-[11px] leading-4">
      {warnings.map((warning) => (
        <li key={warning}>{warning}</li>
      ))}
    </ul>
  );
}
