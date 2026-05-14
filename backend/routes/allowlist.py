"""Path allowlist for the UI backend (control plane) component.

The backend exposes management/admin endpoints consumed by the UI: keys, users,
teams, orgs, customers, budgets, tags, workflows, model management, spend &
analytics, settings (router/cache/cost-tracking/fallbacks), SSO/onboarding,
audit logs, debug, enterprise admin, and UI bootstrap helpers (logo, favicon,
.well-known config).

Anything LLM data-plane is dropped — those run on the gateway component.
"""

## Prefixes use trailing slashes so e.g. ``"/login"`` does not silently
## capture a future ``/login_callback`` route. Bare paths that are themselves
## a route (``/login``, ``/audit``, ``/fallback`` …) live in
## ``BACKEND_EXACT_PATHS`` instead, paired with a ``"/foo/"`` prefix when
## sub-paths exist.
BACKEND_PATH_PREFIXES: tuple[str, ...] = (
    # Identity / access
    "/key/",
    "/v2/key/",
    "/user/",
    "/v2/user/",
    "/team/",
    "/v2/team/",
    "/organization/",
    "/customer/",
    "/end_user/",
    "/sso/",
    "/v3/login/",
    "/onboarding/",
    "/audit/",
    "/oauth/",
    "/invitation/",
    "/jwt/",
    # Models & routing config
    "/model/",
    "/v1/model/info",
    "/v2/model/",
    "/model_group/",
    "/model_access_group/",
    "/model_hub/",
    "/v1/access_group",
    "/access_group/",
    "/router/",
    "/adaptive_router/",
    "/fallback/",
    "/cost/",
    "/credentials/",
    "/provider/budgets",
    # Tools / agents (registry & policy admin)
    "/v1/tool/",
    "/v1/agents",
    # Guardrails admin
    "/v2/guardrails/",
    # MCP server admin + BYOK OAuth flow (UI-initiated) + dynamic per-server endpoints
    "/v1/mcp/",
    "/test/",
    "/{mcp_server_name}/",
    # Budgets / tags / workflows / memory mgmt
    "/budget/",
    "/tag/",
    "/workflow/",
    "/v1/workflows/",
    "/project/",
    "/memory/",
    "/mcp/",
    # Spend / analytics
    "/spend/",
    "/analytics/",
    "/global/",
    "/usage/",
    "/daily/",
    # Caching admin
    "/cache/",
    "/caching/",
    # Callbacks / hooks
    "/callbacks/",
    # Alerting / email / IP allowlist
    "/alerting/",
    "/email/",
    "/add/allowed_ip",
    "/delete/allowed_ip",
    "/get/",
    # Enterprise admin
    "/enterprise/",
    # Debug / config / profiling
    "/debug/",
    "/config/",
    "/memory-usage-in-mem-cache",
    "/lazy/",
    # Admin reload / schedule
    "/reload/",
    "/schedule/",
    "/update/",
    "/upload/",
    # Dev / admin utilities
    "/utils/",
    # UI bootstrap helpers (assets the dashboard fetches)
    "/get_logo_url",
    "/get_image",
    "/get_favicon",
    "/.well-known/",
    "/litellm/.well-known/",
    "/ui_discovery/",
    "/ui-config",
    "/public/",
    "/robots.txt",
    # Health (k8s probes)
    "/health",
)

BACKEND_EXACT_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/routes",
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
        # Bare paths that would otherwise rely on broad ``startswith`` prefixes.
        "/login",
        "/v2/login",
        "/v3/login",
        "/logout",
        "/token",
        "/audit",
        "/credentials",
        "/fallback",
        "/active/callbacks",
        "/team_callback",
        "/settings",
        "/router_settings",
        "/cache_settings",
        "/cost_tracking",
        "/sso_settings",
        "/user_agent",
        "/otel-spans",
        "/in_product_nudges",
    }
)
