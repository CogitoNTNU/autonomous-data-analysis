import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { WorkflowSnapshot } from "@/api/workflows";
import { usePlannerSession } from "@/features/analysis-chat/usePlannerSession";

const file = new File(["age\n10\n30\n"], "ages.csv");
const preview = { fileName: "ages.csv", fileSize: 10, rowCount: 2, columnCount: 1, columns: ["age"], rows: [["10"], ["30"]] };
const initial: WorkflowSnapshot = {
  runId: "run-1", checkpointId: "checkpoint-1", status: "running", activeAgent: "planner",
  question: null, plan: null, report: null, analysis: null, interpretation: null, critique: null, answer: null, error: null,
  dialogue: [], analysisRound: 1, acceptsMessages: false,
};
const answer = { text: "Age summary", findings: [], limitations: [], figureIds: [], followUps: [] };
const done: WorkflowSnapshot = { ...initial, status: "completed", activeAgent: null, answer, acceptsMessages: true };
const turn = { analysisRound: 1, referencedIds: [], startsAnalysis: false, failed: false };
function fakeClient() {
  return {
    registerDataset: vi.fn().mockResolvedValue({ dataset_id: "dataset-1" }),
    start: vi.fn().mockResolvedValue(initial),
    status: vi.fn().mockResolvedValue({ ...initial, status: "completed", answer }),
    resume: vi.fn().mockResolvedValue(initial),
    message: vi.fn().mockResolvedValue({ ...done, status: "running" }),
  };
}
async function completeRun(client: ReturnType<typeof fakeClient>) {
  client.start.mockResolvedValue(done);
  const hook = renderHook(() => usePlannerSession(client));
  await act(async () => { await hook.result.current.acceptDataset(preview, file); });
  act(() => hook.result.current.submitQuestion("Describe age"));
  await waitFor(() => expect(hook.result.current.acceptsMessages).toBe(true));
  return hook.result;
}

describe("harness session", () => {
  it("starts once and polls until the final answer is automatically shown", async () => {
    const client = fakeClient();
    const { result } = renderHook(() => usePlannerSession(client));
    await act(async () => { await result.current.acceptDataset(preview, file); });
    act(() => result.current.submitQuestion("Describe age"));
    await waitFor(() => expect(client.start).toHaveBeenCalledWith(expect.objectContaining({
      datasetId: "dataset-1", question: "Describe age",
    }), expect.any(AbortSignal)));
    await waitFor(() => expect(result.current.phase).toBe("complete"), { timeout: 3000 });
    expect(result.current.answer?.text).toBe("Age summary");
    expect(client.start).toHaveBeenCalledTimes(1);
    expect(client.resume).not.toHaveBeenCalled();
  });

  it("answers clarification on the same run without resending results or CSV", async () => {
    const client = fakeClient();
    client.start.mockResolvedValue({ ...initial, status: "needs_clarification", question: "Which column?" });
    const { result } = renderHook(() => usePlannerSession(client));
    await act(async () => { await result.current.acceptDataset(preview, file); });
    act(() => result.current.submitQuestion("Describe it"));
    await waitFor(() => expect(result.current.phase).toBe("clarification_input"));
    expect(client.status).not.toHaveBeenCalled();
    act(() => result.current.submitQuestion("age"));
    await waitFor(() => expect(client.resume).toHaveBeenCalledWith({
      runId: "run-1", checkpointId: "checkpoint-1", answer: "age",
    }, expect.any(AbortSignal)));
    expect(client.start).toHaveBeenCalledTimes(1);
  });

  it("discards a late response after replacing the dataset", async () => {
    const client = fakeClient();
    let finish!: (value: WorkflowSnapshot) => void;
    client.start.mockReturnValue(new Promise<WorkflowSnapshot>((resolve) => { finish = resolve; }));
    const { result } = renderHook(() => usePlannerSession(client));
    await act(async () => { await result.current.acceptDataset(preview, file); });
    act(() => result.current.submitQuestion("Describe age"));
    await waitFor(() => expect(client.start).toHaveBeenCalled());
    act(() => result.current.replaceDataset());
    await act(async () => finish(initial));
    expect(result.current.dataset).toBeNull();
    expect(result.current.phase).toBe("idle");
    expect(client.start.mock.calls[0][1].aborted).toBe(true);
    expect(client.status).not.toHaveBeenCalled();
  });

  it("stops polling and displays a backend error", async () => {
    const client = fakeClient();
    client.status.mockRejectedValue(new Error("Workflow storage is unavailable"));
    const { result } = renderHook(() => usePlannerSession(client));
    await act(async () => { await result.current.acceptDataset(preview, file); });
    act(() => result.current.submitQuestion("Describe age"));
    await waitFor(() => expect(result.current.phase).toBe("error"), { timeout: 3000 });
    expect(result.current.error).toBe("Workflow storage is unavailable");
    expect(client.status).toHaveBeenCalledTimes(1);
  });

  it("sends follow-up messages to the same run and shows them until answered", async () => {
    const client = fakeClient();
    const result = await completeRun(client);
    client.status.mockResolvedValue({ ...done, dialogue: [
      { ...turn, role: "user", content: "Why?" }, { ...turn, role: "assistant", content: "Missing ages." },
    ] });
    act(() => result.current.submitQuestion("Why?"));
    expect(result.current.pendingMessage).toBe("Why?");
    expect(client.message).toHaveBeenCalledWith({ runId: "run-1", checkpointId: "checkpoint-1", message: "Why?" }, expect.any(AbortSignal));
    await waitFor(() => expect(result.current.dialogue).toHaveLength(2), { timeout: 3000 });
    expect(result.current.pendingMessage).toBeNull();
    expect(result.current.phase).toBe("complete");
    expect(client.start).toHaveBeenCalledTimes(1);
  });

  it("keeps the previous answer when a follow-up starts a new analysis round", async () => {
    const client = fakeClient();
    const result = await completeRun(client);
    client.message.mockResolvedValue({ ...done, status: "running", answer: null, analysisRound: 2, acceptsMessages: false });
    client.status.mockResolvedValue({ ...done, analysisRound: 2, answer: { ...answer, text: "Score summary" } });
    act(() => result.current.submitQuestion("Describe score too"));
    await waitFor(() => expect(result.current.answer?.text).toBe("Score summary"), { timeout: 3000 });
    expect(result.current.rounds).toEqual([{ round: 1, answer, figures: [], tables: [] }]);
    act(() => result.current.resetQuestion());
    expect(result.current.rounds).toEqual([]);
  });

  it("cannot start with a failed upload", async () => {
    const client = fakeClient();
    client.registerDataset.mockRejectedValue(new Error("Invalid CSV"));
    const { result } = renderHook(() => usePlannerSession(client));
    await act(async () => { await result.current.acceptDataset(preview, file); });
    act(() => result.current.submitQuestion("Describe age"));
    expect(result.current.error).toBe("Invalid CSV");
    expect(client.start).not.toHaveBeenCalled();
  });
});
