#!/bin/bash

# Kill all background jobs on exit
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

echo "🚀 Starting Research Advisor Swarm..."
echo "Press Ctrl+C to stop all agents."

# 1. Start Agents in background
python researcher.py &
PID1=$!
echo " - Researcher started ($PID1)"

python advisor.py &
PID2=$!
echo " - Advisor started ($PID2)"

python validator.py &
PID3=$!
echo " - Validator started ($PID3)"

python planner.py &
PID4=$!
echo " - Planner started ($PID4)"

# Wait for agents to register
sleep 3

# 2. Run the Client (Interactive)
echo "✅ Swarm ready. Starting Client..."
python client.py
