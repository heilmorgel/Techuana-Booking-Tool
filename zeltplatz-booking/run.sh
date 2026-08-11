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

mkdir -p "${DATA_DIR}"

cd /app/backend
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
