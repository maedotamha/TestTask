def transform(text: str) -> str:
    """Deterministically transform an input string (upper-case it).

    Stands in for an expensive/slow external transformation call, which is
    why results are cached per unique input string instead of recomputed.
    Must stay deterministic: the cache key is the input text alone.
    """
    return text.upper()
