import { errorStatus } from "@/api/payload/error-status";
import { field } from "@/api/payload/field";
import { isRecord } from "@/api/payload/is-record";
import { requiredText } from "@/api/payload/required-text";
import { stringList } from "@/api/payload/string-list";
import type { ChatAnswer } from "@/types/planner";

export type AnswerResult =
  | { status: "answer"; answer: ChatAnswer }
  | { status: "error"; message: string };

export function mapAnswerPayload(payload: unknown): AnswerResult {
  const failure = errorStatus(payload, "Chat");
  if (failure) {
    return failure;
  }
  return { status: "answer", answer: toAnswer(field(payload, "answer")) };
}

function toAnswer(value: unknown): ChatAnswer {
  if (!isRecord(value)) {
    throw new Error("Chat returned no answer");
  }
  return {
    text: requiredText(value.text, "Chat"),
    followUps: stringList(value.follow_up_suggestions),
  };
}
