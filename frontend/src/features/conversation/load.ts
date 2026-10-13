import type { StoredConversation } from "../../types/conversation";
import { CONVERSATION_STORAGE_KEY } from "./constants";
import { isPastDeadline } from "./expiry";
import type { KeyValueStore } from "./keyValueStore";
import { parseStored } from "./parse";

export function loadConversation(
  store: KeyValueStore,
  now: Date,
): StoredConversation | null {
  const raw = store.getItem(CONVERSATION_STORAGE_KEY);
  if (raw === null) {
    return null;
  }
  const conversation = parseStored(raw);
  if (conversation === null || isPastDeadline(conversation.expires_at, now)) {
    store.removeItem(CONVERSATION_STORAGE_KEY);
    return null;
  }
  return conversation;
}
