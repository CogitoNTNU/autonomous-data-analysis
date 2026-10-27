import { mapAnalysisPayload, type AnalysisResult } from "@/api/analysis-response";
import { mapAnswerPayload, type AnswerResult } from "@/api/answer-response";
import { mapCritiquePayload, type CritiqueResult } from "@/api/critique-response";
import {
  mapInterpretationPayload,
  type InterpretationResult,
} from "@/api/interpretation-response";
import type {
  AnalysisAsk,
  AnswerAsk,
  CritiqueAsk,
  InterpretationAsk,
  PlannerAsk,
  PlannerClient,
  PlannerResult,
  PreprocessAsk,
} from "@/api/planner-client";
import { mapPlannerPayload } from "@/api/planner-response";
import { post } from "@/api/post";
import { postJson } from "@/api/post-json";
import {
  mapPreprocessingPayload,
  type PreprocessResult,
} from "@/api/preprocessing-response";

export type {
  AnalysisAsk,
  AnswerAsk,
  CritiqueAsk,
  InterpretationAsk,
  PlannerAsk,
  PlannerClient,
  PlannerMessage,
  PlannerResult,
  PreprocessAsk,
} from "@/api/planner-client";

export const browserPlanner: PlannerClient = {
  registerDataset,
  ask,
  preprocess,
  analyze,
  interpret,
  critique,
  present,
};

async function registerDataset(file: File): Promise<{ dataset_id: string }> {
  const payload = await post("/api/datasets", await file.text(), "text/csv");
  if (!isRegistration(payload)) {
    throw new Error("The dataset was not registered");
  }
  return payload;
}

async function ask(input: PlannerAsk): Promise<PlannerResult> {
  const payload = await post(
    "/api/planner",
    JSON.stringify({
      dataset_id: input.datasetId,
      question: input.question,
      messages: input.messages,
      csv: input.csv,
    }),
    "application/json",
  );
  return mapPlannerPayload(payload);
}

async function preprocess(input: PreprocessAsk): Promise<PreprocessResult> {
  const payload = await post(
    "/api/preprocessing",
    JSON.stringify({
      dataset_id: input.datasetId,
      csv: input.csv,
      plan: input.plan,
    }),
    "application/json",
  );
  return mapPreprocessingPayload(payload);
}

async function analyze(input: AnalysisAsk): Promise<AnalysisResult> {
  return mapAnalysisPayload(await postJson("/api/analysis", input));
}

async function interpret(input: InterpretationAsk): Promise<InterpretationResult> {
  return mapInterpretationPayload(await postJson("/api/interpretation", input));
}

async function critique(input: CritiqueAsk): Promise<CritiqueResult> {
  return mapCritiquePayload(await postJson("/api/critic", input));
}

async function present(input: AnswerAsk): Promise<AnswerResult> {
  return mapAnswerPayload(await postJson("/api/chat", chatBody(input)));
}

function chatBody(input: AnswerAsk) {
  return {
    interpretation: {
      summary: input.interpretation.summary,
      findings: presentedFindings(input.interpretation.findings),
      limitations: input.interpretation.limitations,
      unanswered_questions: input.interpretation.unanswered,
    },
    critique: {
      decision: input.critique.decision,
      required_changes: input.critique.requiredChanges,
    },
    artifacts: presentedArtifacts(input.artifacts),
  };
}

function presentedFindings(findings: AnswerAsk["interpretation"]["findings"]) {
  return findings.flatMap((finding) => {
    const resultIds = finding.resultIds.filter((id) => id.trim().length > 0);
    if (finding.claim.trim().length === 0 || resultIds.length === 0) {
      return [];
    }
    return [{ claim: finding.claim, result_ids: resultIds }];
  });
}

function presentedArtifacts(artifacts: AnswerAsk["artifacts"]) {
  return artifacts.flatMap((artifact) => {
    if (artifact.type !== "figure" && artifact.type !== "table") {
      return [];
    }
    if (artifact.artifact_id.trim().length === 0) {
      return [];
    }
    return [{ artifact_id: artifact.artifact_id, type: artifact.type }];
  });
}

function isRegistration(payload: unknown): payload is { dataset_id: string } {
  if (typeof payload !== "object" || payload === null) {
    return false;
  }
  return typeof Reflect.get(payload, "dataset_id") === "string";
}
