import type {
  ConversationMessage,
  DatasetReference,
  StoredConversation,
} from "../../types/conversation";
import { CONVERSATION_STORAGE_KEY } from "./constants";
import { InvalidConversationMessage, InvalidDatasetReference } from "./errors";
import { conversationDeadline } from "./expiry";
import { isDataset, isMessage } from "./guards";
import type { KeyValueStore } from "./keyValueStore";
import { loadConversation } from "./load";

export function rememberMessage(
  store: KeyValueStore,
  message: ConversationMessage,
  dataset: DatasetReference,
  now: Date,
): StoredConversation {
  if (!isMessage(message)) {
    throw new InvalidConversationMessage();
  }
  const existing = loadConversation(store, now);
  const next =
    existing === null
      ? startConversation(message, dataset, now)
      : appendMessage(existing, message);
  store.setItem(CONVERSATION_STORAGE_KEY, JSON.stringify(next));
  return next;
}

function startConversation(
  message: ConversationMessage,
  dataset: DatasetReference,
  now: Date,
): StoredConversation {
  if (!isDataset(dataset)) {
    throw new InvalidDatasetReference();
  }
  return {
    messages: [message],
    dataset,
    expires_at: conversationDeadline(now),
  };
}

function appendMessage(
  conversation: StoredConversation,
  message: ConversationMessage,
): StoredConversation {
  return {
    messages: [...conversation.messages, message],
    dataset: conversation.dataset,
    expires_at: conversation.expires_at,
  };
}
