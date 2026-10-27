import { isRecord } from "@/api/payload/is-record";

export function records(value: unknown, name: string): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    throw new Error(`${name} returned an unreadable response`);
  }
  return value.filter(isRecord);
}
