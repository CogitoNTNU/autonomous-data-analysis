import type { KeyValueStore } from "./keyValueStore";

export function browserConversationStore(): KeyValueStore {
  return window.localStorage;
}
