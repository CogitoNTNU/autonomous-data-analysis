import { isRecord } from "@/api/payload/is-record";
import { requiredText } from "@/api/payload/required-text";
import { stringList } from "@/api/payload/string-list";
import type { DialogueTurn } from "@/types/dialogue";

export function mapDialogue(value: unknown): DialogueTurn[] {
  if (!Array.isArray(value)) throw new Error("Unreadable workflow dialogue");
  return value.map((turn) => {
    if (!isRecord(turn) || (turn.role !== "user" && turn.role !== "assistant")) {
      throw new Error("Unreadable workflow dialogue");
    }
    return {
      role: turn.role,
      content: requiredText(turn.content, "Chat"),
      analysisRound: analysisRound(turn.analysis_round),
      referencedIds: stringList(turn.referenced_ids),
      startsAnalysis: turn.starts_analysis === true,
      failed: turn.failed === true,
    };
  });
}

function analysisRound(value: unknown): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    throw new Error("Unreadable workflow dialogue");
  }
  return value;
}
