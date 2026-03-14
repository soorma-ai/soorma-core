#!/usr/bin/env bash
# start.sh — Example 13: A2A Gateway
# Starts the internal research agent, then the A2A gateway service.
# Ctrl+C shuts down all background processes cleanly.
set -e
trap 'echo; echo "Shutting down..."; kill $(jobs -p) 2>/dev/null; wait 2>/dev/null' EXIT INT TERM

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate the repo-root venv if present
if [[ -f "../../.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "../../.venv/bin/activate"
fi

echo "============================================================"
echo " Example 13 — A2A Gateway"
echo "============================================================"
echo ""
echo "Prerequisites:"
echo "  • soorma dev stack running (Registry + Event Service)"
echo "  • .env file copied from .env.example and configured"
echo ""

# Validate environment
if [[ ! -f ".env" ]]; then
    echo "ERROR: .env not found. Copy .env.example → .env and fill in your tenant IDs."
    exit 1
fi

# Start the internal research agent first so it can register before the gateway serves traffic
echo "▶ Starting internal research agent..."
python internal_agent.py &
AGENT_PID=$!

sleep 2  # let agent register with Registry + subscribe to NATS

echo "▶ Starting A2A gateway service on port ${GATEWAY_PORT:-9000}..."
python gateway_service.py &
GATEWAY_PID=$!

sleep 1

echo ""
echo "============================================================"
echo " A2A Gateway ready!"
echo "============================================================"
echo ""
echo "Discover agent capabilities:"
echo "  curl -s http://localhost:${GATEWAY_PORT:-9000}/.well-known/agent.json | python -m json.tool"
echo ""
echo "Send an A2A task:"
echo "  curl -s -X POST http://localhost:${GATEWAY_PORT:-9000}/a2a/tasks/send \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"id\":\"task-001\",\"message\":{\"role\":\"user\",\"parts\":[{\"type\":\"text\",\"text\":\"Research quantum computing\"}]}}' \\"
echo "    | python -m json.tool"
echo ""
echo "Press Ctrl+C to stop."
echo ""

wait
