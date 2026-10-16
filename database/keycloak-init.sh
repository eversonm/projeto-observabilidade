#!/bin/sh
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_user="$KEYCLOAK_DB_USER" \
  -v app_password="$KEYCLOAK_DB_PASSWORD" \
  -v monitor_user="$KEYCLOAK_EXPORTER_USER" \
  -v monitor_password="$KEYCLOAK_EXPORTER_PASSWORD" \
  -v app_database="$POSTGRES_DB" <<'SQL'
CREATE ROLE :"app_user" LOGIN PASSWORD :'app_password';
GRANT ALL PRIVILEGES ON DATABASE :"app_database" TO :"app_user";
GRANT ALL PRIVILEGES ON SCHEMA public TO :"app_user";
CREATE ROLE :"monitor_user" LOGIN PASSWORD :'monitor_password';
GRANT pg_monitor TO :"monitor_user";
GRANT CONNECT ON DATABASE :"app_database" TO :"monitor_user";
SQL

