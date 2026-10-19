import type { ClarificationRequest } from "@/types/planner";

export function getPrototypeClarification(
  question: string,
  columns: string[],
): ClarificationRequest | null {
  if (!/\b(largest|biggest)\b/i.test(question)) {
    return null;
  }

  const normalizedColumns = new Set(
    columns.map((column) => column.trim().toLowerCase()),
  );
  const options = [];

  if (normalizedColumns.has("body_mass_g")) {
    options.push({ id: "body_mass_g", label: "Body mass" });
  }
  if (normalizedColumns.has("flipper_length_mm")) {
    options.push({ id: "flipper_length_mm", label: "Flipper length" });
  }

  if (options.length < 2) {
    return null;
  }

  return {
    reason: "ambiguous_objective",
    question: "What do you mean by “largest”?",
    description:
      "This dataset has more than one measure of size. Choose one so I can create the right plan.",
    options: [
      ...options,
      { id: "custom", label: "I’ll explain it myself" },
    ],
  };
}
