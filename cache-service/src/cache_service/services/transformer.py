def transform(text: str) -> str:
    """Deterministically transform an input string.

    Stands in for an expensive/slow external transformation call, which is
    why results are cached per unique input string instead of recomputed.
    """
    return text[::-1].upper()
