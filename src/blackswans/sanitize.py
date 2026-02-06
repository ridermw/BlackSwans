"""Input sanitization utilities."""


def sanitize_ticker(ticker: str) -> str:
    """Sanitize a ticker symbol for safe use in filesystem paths.

    Keeps only alphanumeric characters plus ``^``, ``-``, and ``_``.
    All other characters are replaced with ``_``.
    """
    return "".join(c if c.isalnum() or c in "^-_" else "_" for c in ticker)
