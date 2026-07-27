"""Live-route introspection helpers for dependency-wiring completeness pins.

Extracted from `test_api/test_rate_limit_routes.py` (#199) so the AI quota /
entitlement pin (#340) can reuse the same walker instead of duplicating it.

Imported as `tests.route_introspection` — the same shape as `tests.db_guard`,
which conftest already imports. Deliberately NOT `tests.conftest`: importing
conftest by that dotted name executes it a second time under a distinct module
identity, which rebinds the shared no-op dependencies to fresh function objects
no route was ever built against (see `_shared_dependency_call`'s callers).
"""


def walk_effective_routes(node):
    """Recursively resolve the app's route tree to `_EffectiveRouteContext`
    objects carrying the final `path_format`, `methods` and `dependant`.

    Newer FastAPI (0.138+) doesn't flatten `include_router` calls into
    `app.routes` directly -- each `include_router` call is represented by an
    opaque `fastapi.routing._IncludedRouter` wrapper, and the real,
    prefix-resolved routes only materialize via its
    `effective_candidates()` / `effective_low_priority_routes()` methods as
    `fastapi.routing._EffectiveRouteContext` objects. This walks that structure
    so tests reflect the actual live route table rather than a hardcoded guess.
    """
    from fastapi.routing import _EffectiveRouteContext, _IncludedRouter

    if isinstance(node, _IncludedRouter):
        for child in node.effective_candidates():
            yield from walk_effective_routes(child)
        for child in node.effective_low_priority_routes():
            yield from walk_effective_routes(child)
    elif isinstance(node, _EffectiveRouteContext):
        yield node
    # else: not a route-bearing node (e.g. a plain starlette Mount) -- skip.


def route_dependency_calls():
    """Map every (method, path) on the live `app` to the SET of dependency
    callables declared directly on that route's dependant.

    Deliberately does NOT identify a dependency via its factory's *current*
    value in `app.api.dependencies` (see `_shared_dependency_call` for why
    that's unsafe) -- it just returns the raw per-route dependency sets so the
    caller can derive the shared callable empirically.
    """
    from app.main import app

    calls_by_route = {}
    for top_level_route in app.routes:
        for ctx in walk_effective_routes(top_level_route):
            if not ctx.dependant:
                continue
            calls = {dep.call for dep in ctx.dependant.dependencies}
            for method in ctx.methods:
                if method == "HEAD":
                    continue
                calls_by_route[(method, ctx.path_format)] = calls
    return calls_by_route


def shared_dependency_call(calls_by_route, name):
    """Derive a shared test dependency callable (e.g. `noop_rate_limiter`,
    `noop_ai_quota`) from the routes themselves: the union of every route's
    dependency callables, narrowed by `__name__`. Routes capture each shared
    no-op exactly once at import time, so this yields a set of exactly one
    function object; using the union (not an intersection over the expected
    routes) keeps the derivation working even when a route has LOST the
    dependency, so the missing-route assertion can name it.

    This intentionally avoids reading `deps.get_rate_limiter()` /
    `deps.get_ai_usage_quota()` directly: some unrelated test modules
    (`test_billing_checkout.py`, `test_billing_portal.py`) do
    `from tests.conftest import _sync_users`, which -- because `tests/` has no
    `__init__.py` while pytest itself loads `conftest.py` under the bare module
    name `conftest` -- causes conftest.py to execute a SECOND time under the
    distinct module identity `tests.conftest`. That second execution rebinds
    those factories to brand-new no-op function objects that no route was ever
    built against, so the factories are not a reliable identity source once
    those modules have been collected in the same pytest session. Deriving the
    identity from the routes themselves (by name, not by importing conftest)
    sidesteps that landmine entirely.
    """
    return {
        c
        for calls in calls_by_route.values()
        for c in calls
        if getattr(c, "__name__", "") == name
    }
