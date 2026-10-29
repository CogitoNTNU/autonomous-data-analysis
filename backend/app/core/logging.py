"""Console telemetry for workflow operations; payloads and credentials are excluded."""

import json
import logging
from datetime import UTC, datetime

FIELDS = (
    "attempt",
    "run_id",
    "node",
    "retry_count",
    "revision_count",
    "duration_seconds",
    "error_category",
    "critic_decision",
)


class WorkflowLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
                "event": record.getMessage(),
                "level": record.levelname,
                **{
                    field: getattr(record, field)
                    for field in FIELDS
                    if hasattr(record, field)
                },
            }
        )


def configure_workflow_logging() -> None:
    logger = logging.getLogger("backend.app")
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(WorkflowLogFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
