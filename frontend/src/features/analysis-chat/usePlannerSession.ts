import { useEffect, useRef, useState } from "react";

import { browserWorkflow, type WorkflowClient, type WorkflowSnapshot } from "@/api/workflows";
import { agents } from "@/features/analysis-chat/agents";
import type { DatasetPreview } from "@/types/dataset";
import type { ClarificationOption, ClarificationRequest } from "@/types/planner";

export type PlannerPhase = "idle" | "thinking" | "clarification" | "clarification_input" | "preprocessing" | "analysis" | "interpretation" | "critic" | "chat" | "complete" | "error";
type LoadedDataset = DatasetPreview & { datasetId: string };

export function usePlannerSession(client: WorkflowClient = browserWorkflow) {
  const source = useRef<LoadedDataset | null>(null);
  const [dataset, setDataset] = useState<LoadedDataset | null>(null);
  const [question, setQuestion] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(null);
  const [clarificationAnswer, setClarificationAnswer] = useState<string | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowSnapshot | null>(null);
  const [phase, setPhase] = useState<PlannerPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const active = useRef<{ controller: AbortController; timer?: ReturnType<typeof setTimeout> } | null>(null);
  const upload = useRef(0);

  function cancelRequests() {
    active.current?.controller.abort();
    clearTimeout(active.current?.timer);
    active.current = null;
  }
  useEffect(() => () => { cancelRequests(); upload.current += 1; }, []);

  function resetQuestion() {
    cancelRequests();
    setQuestion("");
    setSubmittedQuestion(null);
    setClarificationAnswer(null);
    setWorkflow(null);
    setError(null);
    setPhase("idle");
  }
  function editQuestion(value: string) { resetQuestion(); setQuestion(value); }
  function replaceDataset() {
    upload.current += 1;
    source.current = null;
    setDataset(null);
    resetQuestion();
  }
  async function acceptDataset(preview: DatasetPreview, file: File) {
    const id = ++upload.current;
    try {
      const registered = await client.registerDataset(file);
      if (id !== upload.current) return false;
      resetQuestion();
      const loaded = { ...preview, datasetId: registered.dataset_id };
      source.current = loaded;
      setDataset(loaded);
      return true;
    } catch (reason: unknown) {
      if (id === upload.current) setError(messageFrom(reason));
      return false;
    }
  }

  function observe(result: WorkflowSnapshot, controller: AbortController) {
    if (controller.signal.aborted) return;
    setWorkflow(result);
    setError(result.error);
    if (result.status === "error") { setPhase("error"); return; }
    if (result.status === "completed") { setPhase("complete"); return; }
    if (result.status === "needs_clarification") { setPhase("clarification_input"); return; }
    setPhase(result.activeAgent && result.activeAgent !== "planner" ? result.activeAgent : "thinking");
    if (active.current) active.current.timer = setTimeout(() => {
      void client.status(result.runId, controller.signal)
        .then((next) => observe(next, controller))
        .catch((reason: unknown) => fail(reason, controller));
    }, 750);
  }
  function fail(reason: unknown, controller: AbortController) {
    if (controller.signal.aborted) return;
    setError(messageFrom(reason));
    setPhase("error");
  }
  function submitQuestion(value: string) {
    const current = source.current;
    if (!current || !value.trim()) return;
    const clarifying = phase === "clarification_input" && workflow?.status === "needs_clarification";
    cancelRequests();
    const controller = new AbortController();
    active.current = { controller };
    setQuestion("");
    setError(null);
    setPhase("thinking");
    if (clarifying && workflow) {
      setClarificationAnswer(value);
      void client.resume({ runId: workflow.runId, checkpointId: workflow.checkpointId, answer: value }, controller.signal)
        .then((result) => observe(result, controller)).catch((reason: unknown) => fail(reason, controller));
    } else {
      setWorkflow(null);
      setClarificationAnswer(null);
      setSubmittedQuestion(value);
      void client.start({ datasetId: current.datasetId, question: value, columns: current.columns }, controller.signal)
        .then((result) => observe(result, controller)).catch((reason: unknown) => fail(reason, controller));
    }
  }
  function answerClarification(option: ClarificationOption) {
    if (option.id === "custom") { setPhase("clarification_input"); return; }
    submitQuestion(option.label);
  }
  const clarification: ClarificationRequest | null = workflow?.question ? {
    reason: "missing_information", question: workflow.question,
    description: "Answer in the message field so the analysis can proceed.", options: [],
  } : null;
  return {
    dataset, question, setQuestion, submittedQuestion, phase, clarification, clarificationAnswer,
    plan: workflow?.plan ?? null, report: workflow?.report ?? null, analysis: workflow?.analysis ?? null,
    interpretation: workflow?.interpretation ?? null, critique: workflow?.critique ?? null, answer: workflow?.answer ?? null,
    error, errorAgent: agents[workflow?.activeAgent ?? "planner"],
    busy: ["thinking", "preprocessing", "analysis", "interpretation", "critic", "chat"].includes(phase),
    acceptDataset, submitQuestion, answerClarification, resetQuestion, replaceDataset, editQuestion,
  };
}

function messageFrom(reason: unknown): string {
  return reason instanceof Error && reason.message.trim() ? reason.message : "The workflow could not be reached";
}
