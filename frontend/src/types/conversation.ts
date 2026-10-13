export type ConversationRole = "system" | "user" | "assistant" | "tool";

export type ConversationMessage = {
  role: ConversationRole;
  content: string;
};

export type DatasetReference = {
  dataset_id: string;
  version: string;
  storage_ref: string;
  schema: Record<string, unknown>;
};

export type StoredConversation = {
  messages: ConversationMessage[];
  dataset: DatasetReference;
  expires_at: string;
};
