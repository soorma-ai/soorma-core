#!/bin/bash

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="research-advisor"
REPO_ROOT="$(cd "$EXAMPLE_DIR/../.." && pwd)"

# Kill all background jobs on exit
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

echo "🚀 Starting Research Advisor Swarm..."
echo "Press Ctrl+C to stop all agents."
echo "🔐 Priming shared example token provider..."
(cd "$REPO_ROOT" && python -m examples.shared.auth "$EXAMPLE_NAME" "$EXAMPLE_DIR") > /dev/null
echo "✓ Example identity bootstrap and token cache ready"

# 1. Start Agents in background
python "$EXAMPLE_DIR/researcher.py" &
PID1=$!
echo " - Researcher started ($PID1)"

python "$EXAMPLE_DIR/advisor.py" &
PID2=$!
echo " - Advisor started ($PID2)"

python "$EXAMPLE_DIR/validator.py" &
PID3=$!
echo " - Validator started ($PID3)"

python "$EXAMPLE_DIR/planner.py" &
PID4=$!
echo " - Planner started ($PID4)"

# Wait for agents to register
sleep 3

# 2. Run the Client (Interactive)
echo "✅ Swarm ready. Starting Client..."
python "$EXAMPLE_DIR/client.py"
