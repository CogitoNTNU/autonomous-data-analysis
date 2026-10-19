import { describe, expect, it } from "vitest";

import { createPrototypeAnalysisPlan } from "@/features/analysis-chat/prototype-plan";

describe("createPrototypeAnalysisPlan", () => {
  it("keeps the user question as the plan objective", () => {
    const plan = createPrototypeAnalysisPlan("Compare sales by city");

    expect(plan.objective).toBe("Compare sales by city");
    expect(plan.status).toBe("draft");
    expect(plan.steps).toHaveLength(3);
  });
});
