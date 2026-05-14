"""Coverage test for the gateway / backend component allowlists.

The componentization scaffold splits the proxy FastAPI app into two runtime
components by trimming the route table inside a wrapped lifespan context:

  gateway.main  -> only paths matched by gateway/routes/allowlist.py
  backend.main  -> only paths matched by backend/routes/allowlist.py

If either allowlist drops a path that was reachable on the monolithic app,
clients hitting that path on the corresponding pod get a 404. This test
guarantees that the union of the two trimmed route sets equals the full set
of routes on the proxy app — i.e. no endpoint is dropped on the floor.

The test reproduces the same predicate that ``gateway/main.py`` and
``backend/main.py`` use, without importing them. The component modules wrap
the shared ``app.router.lifespan_context``; importing them in the test process
would chain wrappers and corrupt the snapshot.
"""

import os
import sys

# Importing ``litellm.proxy.proxy_server`` runs its module-level setup, which
# reads ``DATABASE_URL`` (Prisma) and ``LITELLM_MASTER_KEY``. Tier-zero CI
# runners don't set these. We pin throwaway values before the import so the
# test never depends on a live database or master key.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("LITELLM_MASTER_KEY", "sk-test-component-allowlist")

from fastapi.routing import Mount

# gateway/ and backend/ live at the repo root, not inside litellm/.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.routes.allowlist import BACKEND_EXACT_PATHS, BACKEND_PATH_PREFIXES
from gateway.routes.allowlist import GATEWAY_EXACT_PATHS, GATEWAY_PATH_PREFIXES
from litellm.proxy.proxy_server import app


def _component_paths(routes, exact_paths, path_prefixes) -> set[str]:
    """Reproduce ``gateway.main._is_gateway_route`` / ``backend.main._is_backend_route``."""
    out: set[str] = set()
    for route in routes:
        if isinstance(route, Mount):
            continue
        path = getattr(route, "path", None)
        if path is None:
            continue
        if path in exact_paths or any(path.startswith(p) for p in path_prefixes):
            out.add(path)
    return out


def test_gateway_plus_backend_covers_full_app():
    """Every route on the proxy app must be served by gateway or backend."""
    all_paths = {
        getattr(r, "path")
        for r in app.router.routes
        if not isinstance(r, Mount) and getattr(r, "path", None) is not None
    }
    gateway_paths = _component_paths(
        app.router.routes, GATEWAY_EXACT_PATHS, GATEWAY_PATH_PREFIXES
    )
    backend_paths = _component_paths(
        app.router.routes, BACKEND_EXACT_PATHS, BACKEND_PATH_PREFIXES
    )

    uncovered = all_paths - (gateway_paths | backend_paths)

    assert not uncovered, (
        f"{len(uncovered)} route(s) are not exposed on either component. "
        f"Update gateway/routes/allowlist.py or backend/routes/allowlist.py to cover:\n  "
        + "\n  ".join(sorted(uncovered))
    )


# Routes that are intentionally served by both components: docs/openapi
# scaffolding and k8s health probes (each pod has its own). Anything else
# appearing on both pods is almost certainly a misclassification — a
# management route leaking onto the data-plane gateway, or vice versa.
_ALLOWED_OVERLAP_EXACT: frozenset[str] = frozenset(
    {
        "/",
        "/routes",
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
    }
)


def _is_allowed_overlap(path: str) -> bool:
    return (
        path in _ALLOWED_OVERLAP_EXACT
        or path == "/health"
        or path.startswith("/health/")
    )


def test_gateway_and_backend_do_not_overlap_unexpectedly():
    """No route should land on both components except shared docs/health.

    Catches misclassification bugs that ``test_gateway_plus_backend_covers_full_app``
    misses: a management endpoint accidentally captured by a gateway prefix
    (e.g. via an overly broad ``/{provider}/`` template) would be served by
    *both* pods, silently exposing admin functionality on the data plane.
    """
    gateway_paths = _component_paths(
        app.router.routes, GATEWAY_EXACT_PATHS, GATEWAY_PATH_PREFIXES
    )
    backend_paths = _component_paths(
        app.router.routes, BACKEND_EXACT_PATHS, BACKEND_PATH_PREFIXES
    )

    unexpected_overlap = {
        p for p in (gateway_paths & backend_paths) if not _is_allowed_overlap(p)
    }

    assert not unexpected_overlap, (
        f"{len(unexpected_overlap)} route(s) are served by both gateway and "
        "backend. Move them to exactly one allowlist (or extend "
        "_ALLOWED_OVERLAP_EXACT if it's a deliberately shared route):\n  "
        + "\n  ".join(sorted(unexpected_overlap))
    )


# Sentinel routes used to assert each component's allowlist hasn't drifted.
# Data-plane routes must NOT be exposed on the management backend, and
# management routes must NOT be exposed on the public gateway.
_GATEWAY_ONLY_SENTINELS: tuple[str, ...] = (
    "/v1/chat/completions",
    "/chat/completions",
    "/v1/embeddings",
    "/v1/messages",
    "/v1/responses",
    "/v1/rerank",
    "/anthropic/{endpoint:path}",
    "/bedrock/{endpoint:path}",
    "/vertex_ai/{endpoint:path}",
)
_BACKEND_ONLY_SENTINELS: tuple[str, ...] = (
    "/key/generate",
    "/key/delete",
    "/user/new",
    "/team/new",
    "/audit",
    "/sso/callback",
    "/spend/logs",
    "/v1/agents",
    "/credentials",
)


def test_data_plane_routes_are_not_on_backend():
    """LLM data-plane routes must stay off the management backend."""
    backend_paths = _component_paths(
        app.router.routes, BACKEND_EXACT_PATHS, BACKEND_PATH_PREFIXES
    )
    leaked = [p for p in _GATEWAY_ONLY_SENTINELS if p in backend_paths]
    assert (
        not leaked
    ), "Data-plane routes leaked onto the backend allowlist:\n  " + "\n  ".join(leaked)


def test_management_routes_are_not_on_gateway():
    """Management/admin routes must stay off the public gateway."""
    gateway_paths = _component_paths(
        app.router.routes, GATEWAY_EXACT_PATHS, GATEWAY_PATH_PREFIXES
    )
    leaked = [p for p in _BACKEND_ONLY_SENTINELS if p in gateway_paths]
    assert (
        not leaked
    ), "Management routes leaked onto the gateway allowlist:\n  " + "\n  ".join(leaked)
