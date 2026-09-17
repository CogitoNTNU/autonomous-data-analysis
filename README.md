# Autonomous Data Analysis

An agent-based system that turns structured datasets into clear, verified insights. LangGraph coordinates planning, preprocessing, analysis, interpretation, review, and presentation.

## Architecture

```mermaid
flowchart LR
    D[(CSV / Database)] --> P[Planner]
    P --> R[Preprocessing]
    R --> A[Analysis]
    A --> I[Interpretation]
    I --> C{Critic}
    C -->|Approved| H[Chat]
    C -->|Revise| P
    H --> U[User / App]
```

The agents share validated tools for dataset inspection, preprocessing, statistics, visualization, and optional machine learning.

## Prerequisites

- [Git](https://git-scm.com/)
- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Setup

```bash
git clone https://github.com/CogitoNTNU/autonomous-data-analysis.git
cd autonomous-data-analysis
uv sync
```

## Usage

Inspect the included penguins dataset:

```bash
python kien-test/inspect_dataset.py
```

The command prints the dataset dimensions, missing values, inferred datatypes, and duplicate-row count.

To inspect another CSV file from Python:

```python
from pathlib import Path
import runpy

module = runpy.run_path("kien-test/inspect_dataset.py")
module["inspect_dataset"](Path("path/to/dataset.csv"))
```

## Testing

```bash
uv run pytest
```

## Team

<table>
  <tr>
    <td align="center"><img src="https://github.com/kienple.png?size=100" width="80" alt="Kien Parajes Le"><br><b>Kien Parajes Le</b></td>
    <td align="center"><img src="https://github.com/Sobbel.png?size=100" width="80" alt="Sebastian Jøranger"><br><b>Sebastian Jøranger</b></td>
    <td align="center"><img src="https://github.com/kridahls.png?size=100" width="80" alt="Kristoffer"><br><b>Kristoffer</b></td>
    <td align="center"><img src="https://github.com/DanielSamoylov.png?size=100" width="80" alt="Daniel Samoylov"><br><b>Daniel Samoylov</b></td>
  </tr>
</table>

## License

[MIT](LICENSE)
