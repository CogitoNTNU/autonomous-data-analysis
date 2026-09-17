# Autonomous Data Analysis

An agent-based system that turns structured datasets into clear, verified insights.

## Components

- **Backend:** Python agents, APIs, analysis tools, and data processing.
- **Frontend:** React interface for datasets, questions, and results.
- **Documentation:** MkDocs guides and generated API reference.

## Workflow

```mermaid
flowchart LR
    D[(Dataset)] --> P[Planner] --> R[Preprocessing] --> A[Analysis]
    A --> I[Interpretation] --> C{Critic}
    C -->|Approved| H[Chat] --> U[User]
    C -->|Revise| P
```

See the project [README](https://github.com/CogitoNTNU/autonomous-data-analysis#readme) for prerequisites, setup, and usage.
