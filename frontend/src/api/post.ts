export async function post(path: string, body: string, contentType: string): Promise<unknown> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": contentType },
    body,
  });
  const payload: unknown = await response.json();
  if (!response.ok) {
    throw new Error(messageFrom(payload));
  }
  return payload;
}

function messageFrom(payload: unknown): string {
  if (typeof payload === "object" && payload !== null) {
    const message = Reflect.get(payload, "message");
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  return "The planner could not be reached";
}
