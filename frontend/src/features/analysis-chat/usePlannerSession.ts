import { useRef, useState } from "react";

import type { PlannerClient, PlannerMessage, PlannerResult } from "@/api/planner";
import { browserPlanner } from "@/api/planner";
import {
  continueReviewedPlan,
  type ContinueUpdate,
} from "@/features/analysis-chat/continue-reviewed-plan";
import { agents, type AgentIdentity } from "@/features/analysis-chat/agents";
import { readCsvText } from "@/features/dataset-upload/read-csv-preview";
import type { DatasetPreview } from "@/types/dataset";
import type {
  AnalysisPlan,
  AnalysisReport,
  ChatAnswer,
  ClarificationOption,
  ClarificationRequest,
  CritiqueView,
  InterpretationView,
  PreprocessingReport,
} from "@/types/planner";

export type PlannerPhase =
  | "analysis_ready"
  | "interpretation_ready"
  | "critic_ready"
  | "chat_ready"
  | "idle"
  | "thinking"
  | "clarification"
  | "clarification_input"
  | "plan"
  | "preprocessing"
  | "analysis"
  | "interpretation"
  | "critic"
  | "chat"
  | "complete"
  | "error";

type LoadedDataset = DatasetPreview & { datasetId: string };

export function usePlannerSession(client: PlannerClient = browserPlanner) {
  const source = useRef<{ file: File; dataset: LoadedDataset } | null>(null);
  const [dataset, setDataset] = useState<LoadedDataset | null>(null);
  const [question, setQuestion] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(null);
  const [phase, setPhase] = useState<PlannerPhase>("idle");
  const [clarification, setClarification] = useState<ClarificationRequest | null>(
    null,
  );
  const [clarificationAnswer, setClarificationAnswer] = useState<string | null>(
    null,
  );
  const [plan, setPlan] = useState<AnalysisPlan | null>(null);
  const [report, setReport] = useState<PreprocessingReport | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisReport | null>(null);
  const [interpretation, setInterpretation] = useState<InterpretationView | null>(null);
  const [critique, setCritique] = useState<CritiqueView | null>(null);
  const [answer, setAnswer] = useState<ChatAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorAgent, setErrorAgent] = useState<AgentIdentity>(agents.planner);
  const run = useRef(0);
  const [messages, setMessages] = useState<PlannerMessage[]>([]);

  function resetQuestion() {
    setQuestion("");
    setSubmittedQuestion(null);
    setPhase("idle");
    setClarification(null);
    setClarificationAnswer(null);
    setPlan(null);
    setReport(null);
    setAnalysis(null);
    setInterpretation(null);
    setCritique(null);
    setAnswer(null);
    setError(null);
    setErrorAgent(agents.planner);
    run.current += 1;
    setMessages([]);
  }

  function editQuestion(value: string) {
    resetQuestion();
    setQuestion(value);
  }

  function replaceDataset() {
    source.current = null;
    setDataset(null);
    resetQuestion();
  }

  async function acceptDataset(preview: DatasetPreview, file: File) {
    try {
      const registered = await client.registerDataset(file);
      resetQuestion();
      const loaded = { ...preview, datasetId: registered.dataset_id };
      source.current = { file, dataset: loaded };
      setDataset(loaded);
      return true;
    } catch (reason: unknown) {
      setError(messageFrom(reason));
      return false;
    }
  }

  function submitQuestion(nextQuestion: string) {
    if (phase === "clarification_input") {
      setClarificationAnswer(nextQuestion);
      setQuestion("");
      void requestPlan(nextQuestion, messages);
      return;
    }
    setSubmittedQuestion(nextQuestion);
    setQuestion("");
    setClarification(null);
    setClarificationAnswer(null);
    setPlan(null);
    void requestPlan(nextQuestion, []);
  }

  function answerClarification(option: ClarificationOption) {
    if (option.id === "custom") {
      setQuestion("By largest, I mean ");
      setPhase("clarification_input");
      return;
    }
    setClarificationAnswer(option.label);
    void requestPlan(option.label, messages);
  }

  async function requestPlan(query: string, history: PlannerMessage[]) {
    const current = source.current;
    if (!current) {
      return;
    }
    setPhase("thinking");
    setError(null);
    try {
      applyResult(
        await client.ask({
          datasetId: current.dataset.datasetId,
          question: query,
          messages: history,
          columns: current.dataset.columns,
          csv: await readCsvText(current.file),
        }),
        query,
        history,
      );
    } catch (reason: unknown) {
      setError(messageFrom(reason));
      setPhase("error");
    }
  }

  function applyResult(
    result: PlannerResult,
    query: string,
    history: PlannerMessage[],
  ) {
    if (result.status === "plan") {
      setPlan(result.plan);
      setPhase("plan");
      return;
    }
    if (result.status === "error") {
      setError(result.message);
      setPhase("error");
      return;
    }
    setClarification(result.clarification);
    setMessages([
      ...history,
      { role: "user", content: query },
      { role: "assistant", content: result.clarification.question },
    ]);
    setPhase(hasChoices(result.clarification) ? "clarification" : "clarification_input");
  }

  async function runNextAgent() {
    const current = source.current;
    if (!current || !plan) {
      return;
    }
    const nextStage = {
      plan: "preprocessing",
      analysis_ready: "analysis",
      interpretation_ready: "interpretation",
      critic_ready: "critic",
      chat_ready: "chat",
    } as const;
    const stage = nextStage[phase as keyof typeof nextStage];
    if (!stage) return;
    const id = ++run.current;
    setPhase(stage);
    setError(null);
    const question = clarificationAnswer ?? submittedQuestion ?? plan.objective;
    try {
      await continueReviewedPlan(
        client,
        {
          datasetId: current.dataset.datasetId,
          csv: await readCsvText(current.file),
          plan: plan.source,
          question,
          results: analysis?.results ?? [],
          artifacts: analysis?.artifacts ?? [],
        },
        (update) => {
          if (run.current === id) {
            applyContinue(update);
          }
        },
        stage,
        interpretation,
        critique,
      );
    } catch (reason: unknown) {
      if (run.current !== id) {
        return;
      }
      setError(messageFrom(reason));
      setErrorAgent(agents[stage]);
      setPhase("error");
    }
  }

  function applyContinue(update: ContinueUpdate) {
    if (update.phase === "error") {
      setError(update.message);
      setErrorAgent(update.agent);
      setPhase("error");
      return;
    }
    if (update.phase === "analysis_ready") {
      setReport(update.report);
    }
    if (update.phase === "interpretation_ready") {
      setAnalysis(update.analysis);
    }
    if (update.phase === "critic_ready") {
      setInterpretation(update.interpretation);
    }
    if (update.phase === "chat_ready") {
      setCritique(update.critique);
    }
    if (update.phase === "complete") {
      setAnswer(update.answer);
    }
    setPhase(update.phase);
  }

  return {
    dataset,
    question,
    setQuestion,
    submittedQuestion,
    phase,
    clarification,
    clarificationAnswer,
    plan,
    report,
    analysis,
    interpretation,
    critique,
    answer,
    error,
    errorAgent,
    acceptDataset,
    submitQuestion,
    answerClarification,
    runNextAgent,
    resetQuestion,
    replaceDataset,
    editQuestion,
  };
}

function hasChoices(clarification: ClarificationRequest): boolean {
  return clarification.options.some((option) => option.id !== "custom");
}

function messageFrom(reason: unknown): string {
  if (reason instanceof Error && reason.message.trim()) {
    return reason.message;
  }
  return "The planner could not be reached";
}
