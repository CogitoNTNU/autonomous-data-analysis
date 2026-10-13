import type {
  ConversationMessage,
  ConversationRole,
  DatasetReference,
  StoredConversation,
} from "../../types/conversation";

const roles: readonly ConversationRole[] = [
  "system",
  "user",
  "assistant",
  "tool",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(
  value: Record<string, unknown>,
  keys: readonly string[],
): boolean {
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => key in value);
}

function nonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isRole(value: unknown): value is ConversationRole {
  return typeof value === "string" && roles.some((role) => role === value);
}

export function isMessage(value: unknown): value is ConversationMessage {
  if (!isRecord(value) || !hasExactKeys(value, ["role", "content"])) {
    return false;
  }
  return isRole(value.role) && nonEmpty(value.content);
}

export function isDataset(value: unknown): value is DatasetReference {
  if (!isRecord(value)) {
    return false;
  }
  if (!hasExactKeys(value, ["dataset_id", "version", "storage_ref", "schema"])) {
    return false;
  }
  return (
    nonEmpty(value.dataset_id) &&
    nonEmpty(value.version) &&
    nonEmpty(value.storage_ref) &&
    isRecord(value.schema)
  );
}

function isMessageList(value: unknown): value is ConversationMessage[] {
  return Array.isArray(value) && value.length > 0 && value.every(isMessage);
}

function isTimestamp(value: unknown): value is string {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

export function isStoredConversation(
  value: unknown,
): value is StoredConversation {
  if (!isRecord(value)) {
    return false;
  }
  if (!hasExactKeys(value, ["messages", "dataset", "expires_at"])) {
    return false;
  }
  return (
    isMessageList(value.messages) &&
    isDataset(value.dataset) &&
    isTimestamp(value.expires_at)
  );
}
