import type {
  ConversationMessage,
  DatasetReference,
} from "../../types/conversation";
import { ConversationNotice } from "./ConversationNotice";
import { ConversationTranscript } from "./ConversationTranscript";
import type { KeyValueStore } from "./keyValueStore";
import { useConversation } from "./useConversation";

export const startedAt = new Date("2026-10-13T15:00:00.000Z");

export const dayMs = 24 * 60 * 60 * 1000;

export const penguinDataset: DatasetReference = {
  dataset_id: "penguins",
  version: "1",
  storage_ref: "data/penguins.csv",
  schema: { species: { datatype: "string" } },
};

export const userMessage: ConversationMessage = {
  role: "user",
  content: "Sammenlign kroppsvekt",
};

export const assistantMessage: ConversationMessage = {
  role: "assistant",
  content: "Adelie er lettest.",
};

export function memoryStore(): KeyValueStore {
  const items = new Map<string, string>();
  return {
    getItem(key) {
      return items.get(key) ?? null;
    },
    setItem(key, value) {
      items.set(key, value);
    },
    removeItem(key) {
      items.delete(key);
    },
  };
}

type HarnessProps = {
  store: KeyValueStore;
  now: () => Date;
  draft: ConversationMessage;
};

export function ConversationHarness({ store, now, draft }: HarnessProps) {
  const conversation = useConversation(penguinDataset, store, now);
  return (
    <section>
      <ConversationTranscript messages={conversation.messages} />
      <ConversationNotice message={conversation.error} />
      <p>Utløper {conversation.expiresAt ?? "ingen"}</p>
      <button type="button" onClick={() => conversation.send(draft)}>
        Send
      </button>
    </section>
  );
}
