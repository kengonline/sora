#!/usr/bin/env bash
set -uo pipefail
variant=$1
configuration=${2:-Debug}
probe_app="$(pwd)/.derivedData/Build/Products/${configuration}/Sora.app"
SORA_COMPLETION_PROBE=1 "${probe_app}/Contents/MacOS/Sora" > "${variant}-probe.log" 2>&1 &
probe_pid=$!
sleep 2
# Deliver the normal application-open event to the running SwiftUI app.
open -a "$probe_app"
for i in {1..90}; do
  if ! kill -0 "$probe_pid" 2>/dev/null; then
    wait "$probe_pid"
    probe_status=$?
    cat "${variant}-probe.log"
    if ! grep -Fq 'PROBE RESULT:' "${variant}-probe.log"; then
      echo 'The app exited without exercising the native probe' >&2
      exit 2
    fi
    exit "$probe_status"
  fi
  sleep 1
done
cat "${variant}-probe.log"
kill "$probe_pid"
exit 1
