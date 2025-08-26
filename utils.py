from collections.abc import Sequence
def as_tuple(x: str | Sequence[str]) -> tuple[str, ...]:
    return (x,) if isinstance(x, str) else tuple(x)
