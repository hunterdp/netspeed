#!/bin/bash
set -euo pipefail

# Default configuration
INFLUXDB_HOST="localhost"
INFLUXDB_PORT="8086"
INFLUXDB_DATABASE="speedtest"
INFLUXDB_USER=""
INFLUXDB_PASS=""
CONFIG_FILE="/etc/speedtest.conf"
LOG_FILE="/var/log/speedtest.log"
SHOW_HELP=false

# --- Helper Functions ---

# Log a message to the console and/or a log file.
# Usage: log "message"
log() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$timestamp: $message" | tee -a "$LOG_FILE"
}

# Display usage information.
usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

This script runs a speed test using speedtest-cli and sends the results to an InfluxDB database.

Options:
  -h, --host <host>       InfluxDB host (default: $INFLUXDB_HOST)
  -p, --port <port>       InfluxDB port (default: $INFLUXDB_PORT)
  -d, --database <db>     InfluxDB database (default: $INFLUXDB_DATABASE)
  -u, --user <user>       InfluxDB username (optional)
  -P, --password <pass>   InfluxDB password (optional)
  -c, --config <file>     Path to configuration file (default: $CONFIG_FILE)
  -l, --log <file>        Path to log file (default: $LOG_FILE)
  --help                  Show this help message.
EOF
}

# Check for required command-line tools.
check_dependencies() {
    local missing_deps=0
    for cmd in speedtest-cli jq curl; do
        if ! command -v "$cmd" &> /dev/null; then
            log "Error: Required command '$cmd' is not installed."
            missing_deps=1
        fi
    done
    if [[ $missing_deps -eq 1 ]]; then
        exit 1
    fi
}

# --- Main Script ---

# Load configuration from file, if it exists.
if [[ -f "$CONFIG_FILE" ]]; then
    # shellcheck source=/dev/null
    source "$CONFIG_FILE"
fi

# Parse command-line arguments to override config.
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -h|--host) INFLUXDB_HOST="$2"; shift 2 ;;
        -p|--port) INFLUXDB_PORT="$2"; shift 2 ;;
        -d|--database) INFLUXDB_DATABASE="$2"; shift 2 ;;
        -u|--user) INFLUXDB_USER="$2"; shift 2 ;;
        -P|--password) INFLUXDB_PASS="$2"; shift 2 ;;
        -c|--config) CONFIG_FILE="$2"; shift 2 ;;
        -l|--log) LOG_FILE="$2"; shift 2 ;;
        --help) SHOW_HELP=true; shift ;;
        *) log "Unknown option: $key"; usage; exit 1 ;;
    esac
done

if [[ "$SHOW_HELP" = true ]]; then
    usage
    exit 0
fi

check_dependencies

log "Starting speed test..."

# Run speedtest-cli and get JSON output.
# The --accept-license and --accept-gdpr flags are added to ensure the script runs non-interactively.
json_output=$(speedtest-cli --accept-license --accept-gdpr --json)

if [[ -z "$json_output" ]]; then
    log "Error: speedtest-cli returned no output."
    exit 1
fi

# Parse JSON and build the InfluxDB line protocol string.
ping=$(echo "$json_output" | jq -r '.ping')
download=$(echo "$json_output" | jq -r '.download') # Already in bits/s
upload=$(echo "$json_output" | jq -r '.upload')     # Already in bits/s
hostname=$(hostname -f)

# Ensure values are not null
if [[ "$ping" == "null" || "$download" == "null" || "$upload" == "null" ]]; then
    log "Error: Failed to parse speed test results. Raw output:"
    log "$json_output"
    exit 1
fi

line_protocol="speedtest,host=$hostname ping=$ping,download=$download,upload=$upload"

# Build the curl command.
curl_cmd=(
    curl -sS -XPOST
    "http://$INFLUXDB_HOST:$INFLUXDB_PORT/write?db=$INFLUXDB_DATABASE"
)

# Add credentials if provided.
if [[ -n "$INFLUXDB_USER" && -n "$INFLUXDB_PASS" ]]; then
    curl_cmd+=(-u "$INFLUXDB_USER:$INFLUXDB_PASS")
fi

curl_cmd+=(-d "$line_protocol")

log "Sending data to InfluxDB: $line_protocol"

# Execute the curl command.
if ! response=$("${curl_cmd[@]}"); then
    log "Error sending data to InfluxDB. Response: $response"
    exit 1
fi

log "Speed test data sent successfully."
log "Ping: ${ping}ms, Download: $(($download/1000000))Mbit/s, Upload: $(($upload/1000000))Mbit/s"
