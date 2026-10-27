import { post } from "@/api/post";

export async function postJson(path: string, body: unknown): Promise<unknown> {
  return post(path, JSON.stringify(requestBody(body)), "application/json");
}

function wireRecord(value: unknown): unknown {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return value;
  }
  const source = Reflect.get(value, "source");
  if (typeof source === "object" && source !== null && !Array.isArray(source)) {
    return source;
  }
  return value;
}

function requestBody(body: unknown): unknown {
  if (typeof body !== "object" || body === null) {
    return body;
  }
  if ("datasetId" in body && "plan" in body) {
    return {
      dataset_id: Reflect.get(body, "datasetId"),
      csv: Reflect.get(body, "csv"),
      plan: Reflect.get(body, "plan"),
      question: Reflect.get(body, "question"),
      results: Reflect.get(body, "results"),
      artifacts: Reflect.get(body, "artifacts"),
      interpretation: wireRecord(Reflect.get(body, "interpretation")),
      critique: wireRecord(Reflect.get(body, "critique")),
    };
  }
  return body;
}
