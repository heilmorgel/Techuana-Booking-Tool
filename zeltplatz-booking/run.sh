#!/usr/bin/with-contenv bashio
# ==============================================================================
# Start Zeltplatz Booking add-on
# ==============================================================================
set -e

export DATA_DIR=/data
export DEV_MODE=0

if bashio::config.has_value 'timezone'; then
  export TZ="$(bashio::config 'timezone')"
else
  export TZ="Europe/Vienna"
fi

if bashio::config.has_value 'api_token'; then
  export API_TOKEN="$(bashio::config 'api_token')"
else
  export API_TOKEN=""
fi

# Optional MQTT broker via Supervisor service discovery (mqtt:want).
export MQTT_HOST=""
export MQTT_PORT="1883"
export MQTT_USERNAME=""
export MQTT_PASSWORD=""
export MQTT_SSL="0"
if bashio::services "mqtt" "host" >/dev/null 2>&1; then
  export MQTT_HOST="$(bashio::services mqtt 'host')"
  export MQTT_PORT="$(bashio::services mqtt 'port')"
  export MQTT_USERNAME="$(bashio::services mqtt 'username')"
  export MQTT_PASSWORD="$(bashio::services mqtt 'password')"
  if bashio::services mqtt 'ssl' | grep -qi true; then
    export MQTT_SSL="1"
  fi
  bashio::log.info "MQTT broker discovered at ${MQTT_HOST}:${MQTT_PORT}"
else
  bashio::log.info "No MQTT broker available; HA entities will not be published"
fi

mkdir -p "${DATA_DIR}"

cd /app/backend
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
