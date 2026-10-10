"""Guard: the frontend container gets only the env it reads (#781).

The frontend used the backend's `env_file: .env`, so every OpenAI, Stripe, AWS
and Cloudinary secret sat in a Next.js process that never reads them. An SSR RCE
(#738 was one) would have handed them all over. The frontend now takes an
explicit `environment:` list, and every name on it must be one the frontend's
own code (or better-auth/Next, implicitly) actually reads.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
FRONTEND_SRC = REPO / "frontend" / "src"

# Read by a library rather than by our code, so no `process.env.X` names them.
LIBRARY_READ = {"BETTER_AUTH_SECRET", "NODE_ENV"}
# The frontend reads these, but they disable auth and must never reach a deploy.
NEVER_FORWARDED = {"BYPASS_AUTH", "E2E_ALLOW_BYPASS", "NEXT_PUBLIC_BYPASS_AUTH"}
BACKEND_ONLY = re.compile(r"^(OPENAI|STRIPE|AWS|CLOUDINARY)|^(SENTRY_DSN|AI_API_KEY)$")


def frontend_services():
    for path in sorted(REPO.glob("docker-compose*.yml")):
        service = (yaml.safe_load(path.read_text()) or {}).get("services", {}).get("frontend")
        if service:
            yield path.name, service


def env_names(service):
    env = service.get("environment") or {}
    return {e.split("=", 1)[0] for e in env} if isinstance(env, list) else set(env)


def read_by_frontend():
    names = set()
    for f in FRONTEND_SRC.rglob("*.ts*"):
        if "__tests__" not in f.parts:
            names |= set(re.findall(r"process\.env\.([A-Z0-9_]+)", f.read_text()))
    return names


def test_frontend_takes_no_env_file():
    # An env_file passes the whole file through; no `environment:` list can
    # subtract from it.
    services = list(frontend_services())
    assert services, "no compose file defines a frontend service; guard is vacuous"
    for name, service in services:
        assert "env_file" not in service, name


def test_frontend_env_is_only_what_the_frontend_reads():
    read = read_by_frontend()
    assert {"DATABASE_URL", "EMAIL_SERVICE_PROVIDER"} <= read, "process.env scan missed known reads; guard is vacuous"
    allowed = (read | LIBRARY_READ) - NEVER_FORWARDED
    for name, service in frontend_services():
        assert env_names(service) <= allowed, (name, env_names(service) - allowed)


def test_frontend_gets_no_backend_secret():
    for name, service in frontend_services():
        leaked = {k for k in env_names(service) if BACKEND_ONLY.search(k)}
        assert not leaked, (name, leaked)
