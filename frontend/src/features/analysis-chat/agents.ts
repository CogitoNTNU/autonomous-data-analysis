export type AgentIdentity = {
  name: string;
  initials: string;
};

export const agents = {
  planner: { name: "Planner", initials: "PL" },
  preprocessing: { name: "Preprocessing", initials: "PR" },
  analysis: { name: "Analysis", initials: "AN" },
  interpretation: { name: "Interpretation", initials: "IN" },
  critic: { name: "Critic", initials: "CR" },
  chat: { name: "Chat", initials: "CH" },
} as const satisfies Record<string, AgentIdentity>;
