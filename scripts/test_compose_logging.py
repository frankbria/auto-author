"""Guard: every compose service rotates its json-file logs (#858)."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent


def test_every_service_rotates_its_logs():
    services = yaml.safe_load((REPO / "docker-compose.yml").read_text())["services"]

    assert services, "no services in docker-compose.yml; this guard is vacuous"
    for name, service in services.items():
        logging = service.get("logging") or {}
        assert logging.get("driver") == "json-file", name
        assert logging.get("options", {}).get("max-size"), name
        assert logging.get("options", {}).get("max-file"), name
