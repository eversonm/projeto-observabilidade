#!/bin/sh
set -eu

if [ ! -f .env ]; then
  echo "Crie .env copiando .env.example antes de executar." >&2
  exit 1
fi

set -a
. ./.env
set +a

check_url() {
  name=$1
  url=$2
  attempt=0
  while [ "$attempt" -lt 30 ]; do
    if curl --fail --silent "$url" >/dev/null 2>&1; then
      echo "OK $name"
      return
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  echo "Falha no healthcheck após 60s: $name ($url)" >&2
  exit 1
}

check_url "API liveness" "http://localhost:${API_PORT:-8000}/health/live"
check_url "API readiness / Postgres" "http://localhost:${API_PORT:-8000}/health/ready"
check_url "Keycloak" "http://localhost:${KEYCLOAK_PORT:-8081}/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration"
check_url "API metrics" "http://localhost:${API_PORT:-8000}/metrics"
check_url "Grafana" "http://localhost:3000/api/health"
check_url "Prometheus" "http://localhost:9090/-/ready"
check_url "Alertmanager" "http://localhost:9093/-/ready"
check_url "Loki" "http://localhost:3100/ready"
check_url "Tempo" "http://localhost:3200/ready"

python3 - <<'PY'
import json
import time
from urllib.request import urlopen

required = {
    "api",
    "api-readiness",
    "postgres",
    "keycloak-postgres",
    "host",
    "containers",
    "keycloak",
    "loki",
    "tempo",
    "otel-collector",
    "alloy",
}
for attempt in range(30):
    with urlopen("http://localhost:9090/api/v1/targets", timeout=5) as response:
        targets = json.load(response)["data"]["activeTargets"]
    healthy = {
        target["labels"].get("job")
        for target in targets
        if target.get("health") == "up"
    }
    missing = sorted(required - healthy)
    if not missing:
        print("OK targets Prometheus: " + ", ".join(sorted(required)))
        break
    if attempt == 29:
        raise SystemExit(f"Targets Prometheus sem estado UP: {', '.join(missing)}")
    time.sleep(2)
PY

