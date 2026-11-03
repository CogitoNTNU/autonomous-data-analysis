"""Create provider clients on first use and close them with the run's resources."""

from collections.abc import Callable
from contextlib import ExitStack
from functools import cache
from typing import TypeVar

ModelT = TypeVar("ModelT")


def lazy_model(
    factory: Callable[[], ModelT], resources: ExitStack
) -> Callable[[], ModelT]:
    """Reuse each provider connection within a run; status reads create no clients."""

    @cache
    def load() -> ModelT:
        model = factory()
        close = getattr(model, "close", None)
        if callable(close):
            resources.callback(close)
        return model

    return load
