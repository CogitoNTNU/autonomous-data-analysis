import { isRecord } from "@/api/payload/is-record";
import { requiredText } from "@/api/payload/required-text";

export function errorStatus(
  payload: unknown,
  name: string,
): { status: "error"; message: string } | null {
  if (!isRecord(payload) || typeof payload.status !== "string") {
    throw new Error(`${name} returned an unreadable response`);
  }
  if (payload.status === "error") {
    return { status: "error", message: requiredText(payload.message, name) };
  }
  if (payload.status !== "success") {
    throw new Error(`${name} returned an unknown status`);
  }
  return null;
}
