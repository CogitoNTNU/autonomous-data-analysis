import type {
  ConversationMessage,
  StoredConversation,
} from "../../types/conversation";
import { isStoredConversation } from "./guards";

export function parseStored(raw: string): StoredConversation | null {
  const value = readJson(raw);
  if (!isStoredConversation(value)) {
    return null;
  }
  return copyConversation(value);
}

function readJson(raw: string): unknown {
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return null;
  }
}

function copyConversation(value: StoredConversation): StoredConversation {
  return {
    messages: value.messages.map(copyMessage),
    dataset: {
      dataset_id: value.dataset.dataset_id,
      version: value.dataset.version,
      storage_ref: value.dataset.storage_ref,
      schema: value.dataset.schema,
    },
    expires_at: value.expires_at,
  };
}

function copyMessage(message: ConversationMessage): ConversationMessage {
  return { role: message.role, content: message.content };
}
