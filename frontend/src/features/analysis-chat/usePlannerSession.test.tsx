import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { WorkflowSnapshot } from "@/api/workflows";
import { usePlannerSession } from "@/features/analysis-chat/usePlannerSession";

const file = new File(["age\n10\n30\n"], "ages.csv");
const preview = { fileName: "ages.csv", fileSize: 10, rowCount: 2, columnCount: 1, columns: ["age"], rows: [["10"], ["30"]] };
const initial: WorkflowSnapshot = {
  runId: "run-1", checkpointId: "checkpoint-1", status: "running", activeAgent: "planner",
  question: null, plan: null, report: null, analysis: null, interpretation: null, critique: null, answer: null, error: null,
};
function fakeClient() {
  return {
    registerDataset: vi.fn().mockResolvedValue({ dataset_id: "dataset-1" }),
    start: vi.fn().mockResolvedValue(initial),
    status: vi.fn().mockResolvedValue({ ...initial, status: "completed", answer: { text: "Age summary", findings: [], limitations: [], figureIds: [], followUps: [] } }),
    resume: vi.fn().mockResolvedValue(initial),
  };
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
