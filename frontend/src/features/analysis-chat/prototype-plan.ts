import type { AnalysisPlan } from "@/types/planner";

export function createPrototypeAnalysisPlan(objective: string): AnalysisPlan {
  return {
    id: "prototype-plan",
    objective,
    status: "draft",
    steps: [
      {
        id: "inspect",
        title: "Inspect the relevant columns",
        description:
          "Confirm data types, missing values, and which fields support the question.",
      },
      {
        id: "prepare",
        title: "Prepare the analysis data",
        description:
          "Select the required fields and record any necessary cleaning steps.",
      },
      {
        id: "analyze",
        title: "Analyze and summarize",
        description:
          "Run the appropriate analysis and explain the findings with limitations.",
      },
    ],
    assumptions: [
      "The uploaded CSV is the dataset to use for this analysis.",
    ],
  };
}
