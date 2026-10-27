import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { usePlannerSession } from "@/features/analysis-chat/usePlannerSession";
import type { DatasetPreview } from "@/types/dataset";
import type { AnalysisPlan } from "@/types/planner";

const preview: DatasetPreview = {
  fileName: "penguins.csv",
  fileSize: 32,
  rowCount: 1,
  columnCount: 2,
  columns: ["species", "body_mass_g"],
  rows: [["Adelie", "3750"]],
};

const plan: AnalysisPlan = {
  id: "plan-1",
  objective: "Compare mass",
  status: "draft",
  steps: [],
  assumptions: [],
  source: {
    plan_id: "plan-1",
    objective: "Compare mass",
    required_columns: ["species", "body_mass_g"],
    preprocessing_steps: [],
    analysis_steps: [],
    expected_outputs: [],
    assumptions: [],
  },
};

describe("usePlannerSession", () => {
  it("sends the csv again so a stateless host can read it", async () => {
    const ask = vi.fn().mockResolvedValue({ status: "plan", plan });
    const client = {
      registerDataset: vi.fn().mockResolvedValue({ dataset_id: "dataset-1" }),
      ask,
      ...idleWorkflow(),
    };
    const file = new File(["species,body_mass_g\nAdelie,3750\n"], "penguins.csv", {
      type: "text/csv",
    });
    const { result } = renderHook(() => usePlannerSession(client));

    await act(async () => {
      await result.current.acceptDataset(preview, file);
    });
    act(() => {
      result.current.submitQuestion("Compare mass");
    });

    await waitFor(() => {
      expect(ask).toHaveBeenCalledWith(
        expect.objectContaining({
          datasetId: "dataset-1",
          csv: "species,body_mass_g\nAdelie,3750\n",
        }),
      );
    });
  });

  it("drops the csv when the dataset is replaced", async () => {
    const ask = vi.fn();
    const client = {
      registerDataset: vi.fn().mockResolvedValue({ dataset_id: "dataset-1" }),
      ask,
      ...idleWorkflow(),
    };
    const file = new File(["species,body_mass_g\nAdelie,3750\n"], "penguins.csv");
    const { result } = renderHook(() => usePlannerSession(client));

    await act(async () => {
      await result.current.acceptDataset(preview, file);
    });
    act(() => {
      result.current.replaceDataset();
      result.current.submitQuestion("Compare mass");
    });

    expect(ask).not.toHaveBeenCalled();
  });

  it("keeps the csv out of the session when registration fails", async () => {
    const ask = vi.fn();
    const client = {
      registerDataset: vi.fn().mockRejectedValue(new Error("The dataset was not registered")),
      ask,
      ...idleWorkflow(),
    };
    const file = new File(["species,body_mass_g\nAdelie,3750\n"], "penguins.csv");
    const { result } = renderHook(() => usePlannerSession(client));

    await act(async () => {
      await result.current.acceptDataset(preview, file);
    });
    act(() => {
      result.current.submitQuestion("Compare mass");
    });

    expect(result.current.error).toBe("The dataset was not registered");
    expect(ask).not.toHaveBeenCalled();
  });

  it("continues from the reviewed plan through the later agents", async () => {
    const analyze = vi.fn().mockResolvedValue({
      status: "analysis",
      analysis: {
        steps: [],
        figures: [],
        warnings: [],
        results: [{ step_id: "summarize" }],
        artifacts: [],
      },
    });
    const client = {
      registerDataset: vi.fn().mockResolvedValue({ dataset_id: "dataset-1" }),
      ask: vi.fn().mockResolvedValue({ status: "plan", plan }),
      preprocess: vi.fn().mockResolvedValue({
        status: "report",
        report: {
          changes: [],
          affectedColumns: [],
          rowsBefore: 1,
          rowsAfter: 1,
          warnings: [],
        },
      }),
      analyze,
      interpret: vi.fn().mockResolvedValue({
        status: "interpretation",
        interpretation: {
          summary: "Mass is recorded.",
          findings: [],
          limitations: [],
          unanswered: [],
          source: { summary: "Mass is recorded." },
        },
      }),
      critique: vi.fn().mockResolvedValue({
        status: "critique",
        critique: {
          decision: "approved",
          issues: [],
          requiredChanges: [],
          source: { decision: "approved" },
        },
      }),
      present: vi.fn().mockResolvedValue({
        status: "answer",
        answer: { text: "Mass is recorded.", followUps: [] },
      }),
    };
    const file = new File(["species,body_mass_g\nAdelie,3750\n"], "penguins.csv");
    const { result } = renderHook(() => usePlannerSession(client));

    await act(async () => {
      await result.current.acceptDataset(preview, file);
    });
    act(() => {
      result.current.submitQuestion("Compare mass");
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("plan");
    });
    await act(async () => {
      await result.current.runNextAgent();
    });

    expect(result.current.phase).toBe("analysis_ready");
    expect(analyze).not.toHaveBeenCalled();
    await act(async () => { await result.current.runNextAgent(); });
    expect(result.current.phase).toBe("interpretation_ready");
    expect(client.interpret).not.toHaveBeenCalled();
    await act(async () => { await result.current.runNextAgent(); });
    expect(result.current.phase).toBe("critic_ready");
    expect(client.critique).not.toHaveBeenCalled();
    await act(async () => { await result.current.runNextAgent(); });
    expect(result.current.phase).toBe("chat_ready");
    expect(client.present).not.toHaveBeenCalled();
    await act(async () => { await result.current.runNextAgent(); });

    expect(analyze).toHaveBeenCalledWith(
      expect.objectContaining({
        datasetId: "dataset-1",
        plan: plan.source,
      }),
    );
    expect(result.current.phase).toBe("complete");
    expect(result.current.answer?.text).toBe("Mass is recorded.");
  });
});

function idleWorkflow() {
  return {
    preprocess: vi.fn(),
    analyze: vi.fn(),
    interpret: vi.fn(),
    critique: vi.fn(),
    present: vi.fn(),
  };
}
