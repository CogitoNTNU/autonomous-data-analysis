from backend.app.contracts.models import Artifact, DatasetReference
from backend.app.contracts.state import create_initial_state
from backend.scripts.planner_llm_smoke import _print_state


def test_print_state_includes_artifact_path(capsys):
    dataset = DatasetReference(
        dataset_id="example",
        version="v1",
        storage_ref="data/example.csv",
        schema={},
    )
    state = create_initial_state("Create a chart", dataset)
    state["artifacts"] = [
        Artifact(
            artifact_id="figure-1",
            type="figure",
            storage_ref="backend/data/artifacts/figure-1.png",
        )
    ]

    _print_state(state)

    output = capsys.readouterr().out
    assert "ARTIFACTS" in output
    assert "backend/data/artifacts/figure-1.png" in output
