#!/bin/bash

# Kill all background jobs on exit
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

echo "🚀 Starting Hello World Example..."
echo "Press Ctrl+C to stop all agents."

# 1. Start Agents in background
python tool_agent.py &
PID1=$!
echo " - Tool Agent started ($PID1)"

python worker_agent.py &
PID2=$!
echo " - Worker Agent started ($PID2)"

python planner_agent.py &
PID3=$!
echo " - Planner Agent started ($PID3)"

# Wait for agents to register
sleep 3

# 2. Run the Client (Interactive)
echo "✅ Agents ready. Starting Client..."
python client.py "$@"
