# Backend

Python agents, analysis tools, tests, and example data live here.

```text
backend/
├── app/       # Application and agent code
├── data/      # Local example datasets
├── tests/     # Backend tests
├── pyproject.toml
└── uv.lock
```

From the repository root, install dependencies with `uv sync --project backend`.

## Felles agentkontrakter

Alle agenter importerer `AgentState` fra `backend.app.contracts` og datamodeller
fra `backend.app.contracts.models`. Kontraktene ligger i `app/contracts/`:
`state.py` beskriver LangGraph-state, `models.py` validerer payloads,
`errors.py` definerer feil og `responses.py` definerer felles returformat.

```python
from backend.app.contracts import AgentResponse, create_initial_state
from backend.app.contracts.models import DatasetReference, Plan, PlannerUpdates

state = create_initial_state(
    "Hva er gjennomsnittlig kroppsmasse?",
    DatasetReference(
        dataset_id="penguins",
        version="v1",
        storage_ref="backend/data/penguins.csv",
        schema={"body_mass_g": {"datatype": "integer"}},
    ),
)
response = AgentResponse[PlannerUpdates](
    status="success",
    updates=PlannerUpdates(plan=Plan(plan_id="p1", objective=state["user_query"])),
)
# En node returnerer bare eksplisitt satte outputfelt, med modellobjekter bevart:
updates = {
    name: getattr(response.updates, name)
    for name in response.updates.model_fields_set
}
assert list(updates) == ["plan"]
```

Bruk `AgentResponse[PlannerUpdates].model_validate(payload)` for modellgenerert
output. Tilsvarende finnes `PreprocessingUpdates`, `AnalysisUpdates`,
`InterpretationUpdates`, `CriticUpdates` og `ChatUpdates`; ukjente felt avvises.
`AgentState` er en `TypedDict` og validerer ikke data ved kjøring.
`create_initial_state` oppretter egne lister og kopierer input per kjøring.
Felter som ennå ikke er produsert, er `None` eller tomme lister.

Ved JSON-eksport brukes `model_dump(mode="json", by_alias=True)` slik at
`DatasetReference.dataset_schema` blir kontraktfeltet `schema`. Datasett og
store resultater representeres med lagringsreferanser, ikke selve dataene.

Orkestreringen skal samle `warnings` og `error`, lagre `clarification_question`,
og eie `control` (standard: maksimalt to rettingsrunder). State-felter erstattes;
det er ingen automatiske append-reducere som beholder resultater fra gamle forsøk.
Når plan eller data endres, må orkestreringen nullstille berørte resultater,
figurer, tolkning, vurdering og sluttsvar før videre kjøring.
Referanseintegritet, verktøytilgang, ugyldiggjøring og ruting må håndheves av den
kommende orkestreringen; dette kontraktlaget implementerer ikke agentlogikk.
