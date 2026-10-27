import { afterEach, describe, expect, it, vi } from "vitest";
import { browserWorkflow, mapWorkflow } from "@/api/workflows";

const payload = {
  run_id: "run-1", checkpoint_id: "checkpoint-1", status: "running", active_agent: "planner",
  question: null, plan: null, report: null, analysis: null, interpretation: null, critique: null, answer: null, error: null,
};
afterEach(() => vi.unstubAllGlobals());
describe("workflow API", () => {
  it("sends a start request to the harness endpoint", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload)));
    vi.stubGlobal("fetch", fetcher);
    const result = await browserWorkflow.start({ datasetId: "dataset-1", question: "Describe age", columns: ["age"] });
    expect(fetcher).toHaveBeenCalledWith("/api/workflows", expect.objectContaining({ method: "POST" }));
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ dataset_id: "dataset-1", question: "Describe age" });
    expect(result.runId).toBe("run-1");
  });
  it("maps the final answer", () => {
    expect(mapWorkflow({ ...payload, status: "completed", active_agent: null, answer: {
      text: "Mean age is 20", findings: [], limitations: [], artifact_ids: [], follow_up_suggestions: [],
    } }).answer?.text).toBe("Mean age is 20");
  });
  it("rejects missing answers and unknown agent names", () => {
    expect(() => mapWorkflow({ ...payload, status: "completed" })).toThrow("no answer");
    expect(() => mapWorkflow({ ...payload, active_agent: "unknown" })).toThrow("Unknown workflow agent");
  });
  it("reports empty HTTP responses clearly", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 502 })));
    await expect(browserWorkflow.status("run-1")).rejects.toThrow("empty or unreadable");
  });
  it("preserves server errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "Unknown workflow" }), { status: 400 })));
    await expect(browserWorkflow.status("missing")).rejects.toThrow("Unknown workflow");
  });
});
