import type {
  ConversationMessage,
  DatasetReference,
  StoredConversation,
} from "../../types/conversation";
import { InvalidConversationMessage, InvalidDatasetReference } from "./errors";
import type { KeyValueStore } from "./keyValueStore";
import { rememberMessage } from "./remember";

export type AcceptedMessage = {
  conversation: StoredConversation | null;
  error: string | null;
};

export function acceptMessage(
  store: KeyValueStore,
  message: ConversationMessage,
  dataset: DatasetReference,
  now: Date,
): AcceptedMessage {
  try {
    return {
      conversation: rememberMessage(store, message, dataset, now),
      error: null,
    };
  } catch (error) {
    const text = knownError(error);
    if (text === null) {
      throw error;
    }
    return { conversation: null, error: text };
  }
}

function knownError(error: unknown): string | null {
  if (error instanceof InvalidConversationMessage) {
    return error.message;
  }
  if (error instanceof InvalidDatasetReference) {
    return error.message;
  }
  return null;
}
