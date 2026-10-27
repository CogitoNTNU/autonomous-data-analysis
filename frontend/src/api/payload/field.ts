import { isRecord } from "@/api/payload/is-record";

export function field(payload: unknown, key: string): unknown {
  if (!isRecord(payload)) {
    return undefined;
  }
  return payload[key];
}
