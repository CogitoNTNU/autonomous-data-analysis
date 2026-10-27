import type { AnalysisPlan, PlanStep, StoredPlan, StoredPlanStep } from "@/types/planner";

import { isRecord } from "@/api/payload/is-record";
import type { PlannerResult } from "@/api/planner-client";

type BackendStep = {
  step_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  depends_on?: unknown;
};

export function mapPlannerPayload(payload: unknown): PlannerResult {
  if (!isRecord(payload) || typeof payload.status !== "string") {
    throw new Error("The planner returned an unreadable response");
  }
  if (payload.status === "needs_clarification") {
    return clarification(payload.question);
  }
  if (payload.status === "success") {
    return { status: "plan", plan: toPlan(payload.plan) };
  }
  if (payload.status === "error") {
    return { status: "error", message: text(payload.message) };
  }
  throw new Error("The planner returned an unknown status");
}

function clarification(question: unknown): PlannerResult {
  return {
    status: "clarification",
    clarification: {
      reason: "missing_information",
      question: text(question),
      description: "Answer in the message field so the planner can revise the plan.",
      options: [],
    },
  };
}

function toPlan(value: unknown): AnalysisPlan {
  if (!isRecord(value)) {
    throw new Error("The planner returned no plan");
  }
  const steps = [...stepsOf(value.preprocessing_steps), ...stepsOf(value.analysis_steps)];
  const expected = stringList(value.expected_outputs);
  if (expected.length > 0) {
    steps.push({
      id: "expected-output",
      title: "Expected output",
      description: expected.join(" "),
    });
  }
  return {
    id: text(value.plan_id),
    objective: text(value.objective),
    assumptions: stringList(value.assumptions),
    status: "draft",
    steps,
    source: storedPlan(value),
  };
}

function storedPlan(value: Record<string, unknown>): StoredPlan {
  return {
    plan_id: text(value.plan_id),
    objective: text(value.objective),
    required_columns: stringList(value.required_columns),
    preprocessing_steps: storedSteps(value.preprocessing_steps),
    analysis_steps: storedSteps(value.analysis_steps),
    expected_outputs: stringList(value.expected_outputs),
    assumptions: stringList(value.assumptions),
  };
}

function storedSteps(value: unknown): StoredPlanStep[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isStep).map((step) => ({
    step_id: step.step_id,
    tool_name: step.tool_name,
    arguments: step.arguments,
    depends_on: stringList(step.depends_on),
  }));
}

function stepsOf(value: unknown): PlanStep[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isStep).map(toStep);
}

function toStep(step: BackendStep): PlanStep {
  return {
    id: step.step_id,
    title: step.tool_name.replaceAll("_", " "),
    description: describe(step.arguments),
  };
}

function describe(args: Record<string, unknown>): string {
  const parts = Object.entries(args).map(([key, value]) => {
    return `${key}: ${JSON.stringify(value)}`;
  });
  return parts.join(", ") || "No extra arguments.";
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
}

function text(value: unknown): string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error("The planner left a required field empty");
  }
  return value;
}

function isStep(value: unknown): value is BackendStep {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.step_id === "string" &&
    typeof value.tool_name === "string" &&
    isRecord(value.arguments)
  );
}
