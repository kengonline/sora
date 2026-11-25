#!/usr/bin/env bash
set -uo pipefail
variant=$1
SORA_COMPLETION_PROBE=1 .derivedData/Build/Products/Debug/Sora.app/Contents/MacOS/Sora > "${variant}-probe.log" 2>&1 &
probe_pid=$!
for i in {1..90}; do
  if ! kill -0 "$probe_pid" 2>/dev/null; then
    wait "$probe_pid"
    probe_status=$?
    cat "${variant}-probe.log"
    exit "$probe_status"
  fi
  sleep 1
done
cat "${variant}-probe.log"
kill "$probe_pid"
exit 1
