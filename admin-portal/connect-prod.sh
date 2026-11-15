#!/usr/bin/env bash
# Run the admin portal against the production backend.
#
# The admin API has no public route, so this opens an SSH tunnel to the
# server (local port 8001 -> the server's backend on 8000), then starts the
# portal's dev server pointed at the tunnel. Ctrl+C stops both.
#
#   ./connect-prod.sh
#   then open http://localhost:5175 (or http://<this machine's IP>:5175)
set -euo pipefail

VM=voxeats-server
ZONE=us-central1-a
PROJECT=voxeats
LOCAL_PORT=8001 # 8000 is the local Docker backend

cd "$(dirname "$0")"

tunnel_up() {
  curl -fsS -m 3 "http://127.0.0.1:${LOCAL_PORT}/health" >/dev/null 2>&1
}

TUNNEL_PID=""
cleanup() {
  if [[ -n "$TUNNEL_PID" ]]; then
    echo "Closing the SSH tunnel..."
    kill "$TUNNEL_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if tunnel_up; then
  echo "A tunnel is already open on port ${LOCAL_PORT}; using it."
else
  # Refresh gcloud credentials in the foreground first: the tunnel below runs
  # in the background, where gcloud can't prompt to re-authenticate.
  if ! gcloud auth print-access-token >/dev/null; then
    echo "gcloud is not logged in. Run: gcloud auth login   (then run this script again)" >&2
    exit 1
  fi

  echo "Opening SSH tunnel to ${VM} (local ${LOCAL_PORT} -> server 8000)..."
  gcloud compute ssh "$VM" --zone="$ZONE" --project="$PROJECT" -- \
    -N -L "${LOCAL_PORT}:127.0.0.1:8000" \
    -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 &
  TUNNEL_PID=$!

  for _ in $(seq 1 30); do
    if tunnel_up; then break; fi
    if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
      echo "The SSH tunnel failed to start (check: gcloud auth login, or port ${LOCAL_PORT} already in use)." >&2
      exit 1
    fi
    sleep 1
  done
  if ! tunnel_up; then
    echo "The tunnel opened but the backend did not answer on port ${LOCAL_PORT}." >&2
    exit 1
  fi
  echo "Tunnel is up: the production backend answers."
fi

if [[ ! -d node_modules ]]; then
  npm install
fi

echo
echo "Admin portal (production data!): http://localhost:5175"
echo "Press Ctrl+C to stop the portal and close the tunnel."
echo
VITE_API_TARGET="http://localhost:${LOCAL_PORT}" npm run dev
