"""Provider-independent exceptions handled at application boundaries."""


class ModelProviderError(RuntimeError):
    """A non-transient model request failure, such as invalid credentials."""
