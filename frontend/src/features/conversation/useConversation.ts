import { useState } from "react";

import type {
  ConversationMessage,
  DatasetReference,
  StoredConversation,
} from "../../types/conversation";
import { acceptMessage } from "./accept";
import { browserConversationStore } from "./browserStore";
import type { KeyValueStore } from "./keyValueStore";
import { loadConversation } from "./load";

export type ConversationController = {
  messages: ConversationMessage[];
  expiresAt: string | null;
  error: string | null;
  send: (message: ConversationMessage) => void;
};

export function useConversation(
  dataset: DatasetReference,
  store: KeyValueStore = browserConversationStore(),
  now: () => Date = () => new Date(),
): ConversationController {
  const [conversation, setConversation] = useState<StoredConversation | null>(
    () => loadConversation(store, now()),
  );
  const [error, setError] = useState<string | null>(null);
  const send = (message: ConversationMessage): void => {
    const accepted = acceptMessage(store, message, dataset, now());
    setError(accepted.error);
    if (accepted.conversation !== null) {
      setConversation(accepted.conversation);
    }
  };
  return {
    messages: conversation?.messages ?? [],
    expiresAt: conversation?.expires_at ?? null,
    error,
    send,
  };
}
