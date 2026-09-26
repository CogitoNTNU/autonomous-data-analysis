## Purpose

This repository implements a modular Autonomous Data Analysis system.

LangGraph is responsible for orchestration, shared state, routing, retries,
interrupts, stopping conditions, and workflow loops.

Agents/nodes perform bounded responsibilities.

Tools perform deterministic calculations, data transformations, and other
controlled operations.

---

## Engineering principles

### 1. Prefer simple code

Implement the smallest solution that satisfies the requirement.

Do not introduce abstractions without a concrete use case.

Avoid:
- unnecessary base classes
- deep inheritance
- generic utility modules
- premature framework abstractions
- wrappers around wrappers
- duplicated orchestration logic

### 2. Modular code is mandatory

Each module must have one clearly defined responsibility.

Do not combine:
- orchestration
- domain logic
- storage
- prompts
- tools
- API handling

in the same module.

Keep boundaries between modules explicit.

### 3. Keep functions small and focused

Functions should:
- perform one task
- have typed inputs
- have typed outputs
- avoid hidden side effects

If a function has multiple responsibilities or requires extensive comments
to explain its control flow, split it into smaller functions.

### 4. Explicit contracts

Communication between workflow nodes must use typed Pydantic models.

Do not pass unstructured dictionaries between major components when a stable
domain model can be defined.

Examples of shared contracts:
- DatasetReference
- DatasetMetadata
- AnalysisPlan
- PlanStep
- PreprocessingReport
- AnalysisResult
- ArtifactReference
- Interpretation
- Critique
- WorkflowError
- AnalysisState

### 5. Shared state is the communication layer

Agents do not communicate directly with each other.

Do not use:
- global variables
- hidden module state
- direct agent references
- implicit shared objects

All workflow communication happens through LangGraph state and typed
contracts.

Example:

Planner
  -> writes AnalysisPlan to AnalysisState
  -> LangGraph routes to Preprocessing
  -> Preprocessing reads the plan from AnalysisState

### 6. LangGraph is the orchestrator

LangGraph owns:
- workflow state
- node execution
- routing
- critic loops
- clarification interrupts
- retries
- step limits
- checkpointing

Individual agents must not implement their own competing orchestration layer.

### 7. Deterministic work belongs in tools or executors

LLMs must not:
- calculate statistics directly
- transform datasets directly
- execute arbitrary Python
- access files directly
- query databases directly
- invent analysis results

Use registered tools.

Preprocessing and Analysis should initially be deterministic executors rather
than LLM-driven agents.

### 8. Raw data is immutable

Never modify an uploaded or raw dataset in place.

Every transformation must produce a new dataset version.

The workflow should distinguish between:
- source_dataset: original immutable dataset
- active_dataset: dataset version currently used for analysis

### 9. Separate planning from execution

The Planner defines what should happen.

Tools and executors record what actually happened.

Maintain traceability:

User Query
  -> AnalysisPlan
  -> PlanStep
  -> ToolExecution
  -> AnalysisResult
  -> Finding
  -> FinalResponse

Do not silently change a plan during execution.

### 10. Dependency direction

Preferred dependency direction:

api
  -> graph
  -> agents / executors
  -> contracts

tools
  -> contracts

storage
  -> contracts

Agents may depend on tool interfaces.

Tools must never depend on agents.

Storage must not depend on LangGraph-specific logic.

### 11. Avoid large files

As a guideline:
- split files approaching roughly 300 lines when responsibilities can be separated
- avoid "utils.py" dumping grounds
- create domain-specific modules instead
- keep prompts separate from agent implementation
- keep models/contracts separate from execution logic

### 12. Tests are required

New functionality must include:
- a happy-path test
- a validation/error test
- an edge-case test where relevant

Agent behavior must be testable with model stubs or fakes.

Tool tests must not require an LLM.

Core contracts must be testable without FastAPI or LangGraph.

### 13. No silent fallback

Invalid states should fail explicitly.

Do not silently:
- invent missing columns
- substitute tools
- ignore validation failures
- swallow exceptions
- continue from failed dependencies
- replace unsupported analysis methods
- reuse stale results without recording it

### 14. Tool access must follow least privilege

Each workflow node only receives access to the tools it needs.

Suggested permissions:

Planner (directly callable, read-only dataset inspection only):
- inspect_schema
- get_metadata
- preview_data
- column_profile

Preprocessing:
- handle_missing_values
- remove_duplicates
- change_datatypes
- filter_rows
- select_columns

Analysis:
- descriptive_statistics
- group_aggregate
- correlation_analysis
- categorical_analysis
- visualization tools

Interpretation:
- no data-modifying tools

Critic:
- no data-modifying tools

Chat:
- no analysis tools

### 15. Validate every tool call

The tool registry must reject:
- unknown tools
- invalid arguments
- duplicate tool names
- invalid dataset references
- file access outside approved locations
- arbitrary code execution
- unrestricted SQL unless explicitly supported

### 16. Large outputs belong in artifacts

Do not store complete DataFrames, large tables, binary figures, or model files
inside LangGraph state.

Store them externally and keep only an ArtifactReference in state.

### 17. Logging

Use structured logging.

Log:
- request ID
- node entered/exited
- plan ID
- dataset version
- tool name
- step ID
- duration
- result/artifact ID
- warnings
- critic decision
- revision count
- error category

Never log:
- complete datasets
- credentials
- secrets
- user credentials
- sensitive raw values
- internal stack traces in user-facing responses

### 18. Error handling

Errors must use structured WorkflowError objects.

Retry only transient failures such as:
- temporary storage failures
- temporary database connection failures
- timeouts

Do not retry:
- invalid arguments
- unknown columns
- unsupported data types
- unknown tools
- invalid plan dependencies

All loops must have explicit limits.

### 19. Critic routing should be targeted

A Critic rejection should return to the node responsible for the issue.

Examples:

Interpretation issue
  -> Interpretation

Analysis execution issue
  -> Analysis

Preprocessing issue
  -> Preprocessing

Planning/methodology issue
  -> Planner

Do not rerun the entire workflow unless necessary.

### 20. Pull requests

PRs should be small and focused.

Do not mix:
- new features
- large refactors
- formatting changes
- unrelated cleanup

in the same PR.

Each PR should include:
- typed inputs and outputs
- tests
- error handling
- documentation where relevant
- no unrelated refactoring

---

## Agent and node responsibilities

### Planner

Responsible for:
- understanding the user's objective
- directly calling `inspect_schema`, `get_metadata`, `preview_data`, and
  `column_profile` as needed to understand the dataset
- selecting registered preprocessing and analysis tools for plan steps
- producing a validated AnalysisPlan
- declaring assumptions
- asking for clarification when required

Must not:
- transform datasets
- calculate analysis results
- execute preprocessing, analysis, or data-modifying tools
- produce the final answer

These four inspection tools are bound to the Planner as its complete runtime
tool set. The Planner decides which of them to call and may use their typed
results while constructing or revising a plan. Every call must still pass
through ToolRegistry validation and count toward the LangGraph execution
limits.

### Preprocessing Executor

Responsible for:
- executing preprocessing steps
- validating steps through the registry
- preserving raw data
- creating new dataset versions
- producing a PreprocessingReport

This should be deterministic.

### Analysis Executor

Responsible for:
- resolving step dependencies
- executing analysis and visualization tools
- collecting structured results
- recording sample sizes and warnings
- stopping downstream work when dependencies fail

This should be deterministic.

### Interpretation Agent

Responsible for:
- explaining calculated results
- connecting findings to the user objective
- referencing supporting result IDs
- preserving warnings, limitations, and assumptions

Must not:
- calculate missing values
- invent results
- ignore tool warnings
- make unsupported claims

### Critic Agent

Responsible for:
- checking whether the objective was answered
- checking whether findings are grounded
- checking methodology and data-quality issues
- checking assumptions and warnings
- selecting the correct retry target

### Chat Agent

Responsible for:
- presenting clarification questions
- presenting approved results
- linking artifacts
- preserving important limitations
- supporting follow-up conversation

Must not execute analysis tools.

---

## Node input/output rule

Every node should follow the pattern:

InputModel -> Node -> OutputModel

Each node:
1. Reads only the state fields it needs.
2. Converts them into a typed input model.
3. Performs its bounded responsibility.
4. Returns a typed output.
5. Lets the harness merge the output into shared state.

Do not let nodes return arbitrary data structures.

---

## Dataset ingestion boundary

Raw files or database connections must be registered before entering the
analysis workflow.

The ingestion layer should:
- validate the input
- assign a dataset_id
- create the raw dataset version
- compute a content hash
- store the dataset
- inspect initial metadata
- return a DatasetReference

The workflow should never depend on arbitrary user-provided filesystem paths.

---

## Clarification contract

Clarification should use a structured model rather than a plain string.

Recommended fields:
- reason
- question
- options

Example reasons:
- ambiguous_objective
- missing_information
- missing_column
- unsupported_request

---

## Plan-step dependencies

Plan steps may depend on outputs from earlier steps.

Dependencies must:
- reference valid earlier steps
- contain no cycles
- be resolved by the executor
- never require the Planner to guess future artifact IDs

Use explicit step/output references when later steps depend on earlier results.

---

## Recommended implementation order

Phase 0:
- repository structure
- AGENTS.md
- linting
- formatting
- test setup
- CI

Phase 1:
- shared contracts
- validation tests

Phase 2:
- storage
- dataset ingestion
- dataset versioning

Phase 3:
- Tool interface
- ToolRegistry
- validation
- permissions

Phase 4:
- dataset inspection tools

Phase 5:
- Planner

Phase 6:
- Preprocessing Executor

Phase 7:
- Analysis Executor

Phase 8:
- Interpretation
- Critic

Phase 9:
- LangGraph harness
- routing
- interrupts
- critic loop
- limits

Phase 10:
- Chat
- FastAPI

Phase 11:
- persistent storage
- observability
- tracing

Phase 12:
- additional analysis and visualization tools

Phase 13:
- optional ML functionality

---

## Before implementing a feature

1. Identify the owning module.
2. Define or update its contract.
3. Write validation/tests.
4. Implement the smallest solution.
5. Run tests.
6. Verify dependency direction.
7. Remove dead or duplicated code.
8. Confirm that deterministic work is not being delegated to an LLM.
9. Confirm that state contains references rather than large artifacts.
10. Confirm that tool access is limited to what the node actually needs.

---

## Definition of clean code for this repository

Code is considered clean when:

- responsibilities are obvious from file and module names
- dependencies flow in one direction
- contracts are typed
- business logic can be tested without FastAPI or LangGraph
- deterministic operations do not require an LLM
- nodes do not communicate through hidden state
- raw datasets remain immutable
- results are traceable to tool executions and dataset versions
- a module can be replaced without rewriting unrelated modules
- the simplest adequate implementation is preferred
