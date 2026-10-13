import { CONVERSATION_TTL_MS } from "./constants";

export function conversationDeadline(now: Date): string {
  return new Date(now.getTime() + CONVERSATION_TTL_MS).toISOString();
}

export function isPastDeadline(expiresAt: string, now: Date): boolean {
  return Date.parse(expiresAt) <= now.getTime();
}
