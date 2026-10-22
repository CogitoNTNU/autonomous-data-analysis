import { useEffect, useRef } from "react";
import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AgentDisclosure } from "@/features/analysis-chat/AgentDisclosure";
import { agents } from "@/features/analysis-chat/agents";
import type { AnalysisPlan } from "@/types/planner";

type AnalysisPlanCardProps = {
  plan: AnalysisPlan;
  onRun?: () => void;
  running?: boolean;
};

export function AnalysisPlanCard({ plan, onRun, running = false }: AnalysisPlanCardProps) {
  const action = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = action.current;
    if (element && typeof element.scrollIntoView === "function") {
      element.scrollIntoView({ block: "end" });
    }
  }, []);

  return (
    <AgentDisclosure
      actions={
        onRun && (
          <div className="mt-3 scroll-mb-48" ref={action}>
            <Button disabled={running} onClick={onRun} type="button">
              Continue
            </Button>
          </div>
        )
      }
      agent={agents.planner}
      summary={summary(plan.steps.length)}
    >
      <PlanDetails plan={plan} />
    </AgentDisclosure>
  );
}

function summary(stepCount: number): string {
  const label = stepCount === 1 ? "step" : "steps";
  return `Prepared an analysis plan, ${stepCount} ${label}`;
}

function PlanDetails({ plan }: { plan: AnalysisPlan }) {
  return (
    <Card className="overflow-hidden shadow-none" id="analysis-plan-details">
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0 border-b p-4">
        <div>
          <h2 className="text-xs font-semibold" id="analysis-plan-title">
            Analysis plan
          </h2>
          <p className="mt-1 text-[10px] text-muted-foreground">
            Review the proposed steps before analysis begins.
          </p>
        </div>
        <Badge className="text-[9px]" variant="secondary">
          Draft
        </Badge>
      </CardHeader>
      <CardContent className="p-4">
        <div className="rounded-lg bg-muted/70 px-3 py-2.5">
          <p className="text-[9px] font-semibold uppercase tracking-wide text-muted-foreground">
            Objective
          </p>
          <p className="mt-1 text-xs leading-5">{plan.objective}</p>
        </div>
        <ol aria-label="Plan steps" className="mt-5 space-y-4">
          {plan.steps.map((step, index) => (
            <li className="flex gap-3" key={step.id}>
              <span className="grid size-6 shrink-0 place-items-center rounded-full border border-border bg-background text-[10px] font-semibold">
                {index + 1}
              </span>
              <div className="min-w-0 pt-0.5">
                <h3 className="text-[11px] font-semibold">{step.title}</h3>
                <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
                  {step.description}
                </p>
              </div>
            </li>
          ))}
        </ol>
        {plan.assumptions.length > 0 && <Assumptions items={plan.assumptions} />}
      </CardContent>
    </Card>
  );
}

function Assumptions({ items }: { items: string[] }) {
  return (
    <div className="mt-5 border-t pt-4">
      <p className="text-[10px] font-semibold">Assumptions</p>
      <ul className="mt-2 space-y-1.5">
        {items.map((assumption) => (
          <li
            className="flex gap-2 text-[10px] leading-4 text-muted-foreground"
            key={assumption}
          >
            <Check className="mt-0.5 size-3 shrink-0" />
            <span>{assumption}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
