"""The Terms of Service version an account must have accepted (#1316).

Mirrors ``TERMS_VERSION`` in ``frontend/src/lib/constants/legal.ts``, which is
the source; ``test_terms_gate.py`` fails when the two differ. Change both with
the /terms copy.
"""

TERMS_VERSION = "2026-11-25"


def accepted_current_terms(version: object) -> bool:
    """Versions are ISO dates, so they compare as strings. A missing version,
    as on an account created before #789, counts as older."""
    return isinstance(version, str) and version >= TERMS_VERSION
