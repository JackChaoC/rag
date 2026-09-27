class NotFoundError(LookupError):
    pass


class ConflictError(RuntimeError):
    pass


class DependencyError(RuntimeError):
    pass
