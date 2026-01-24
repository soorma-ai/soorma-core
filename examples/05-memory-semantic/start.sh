#!/bin/bash
# Start script for 04-memory-semantic example

echo "🚀 Starting 04-memory-semantic example..."
echo ""
echo "This example demonstrates LLM-based routing with semantic memory and RAG."
echo ""

# Check if platform services are running
echo "Checking platform services..."
if ! curl -s http://localhost:8083/health > /dev/null 2>&1; then
    echo "❌ Memory Service not responding"
    echo ""
    echo "Please start platform services first:"
    echo "  cd ../../  # Go to soorma-core root"
    echo "  soorma dev --build"
    echo ""
    exit 1
fi

echo "✓ Memory Service is running"
echo ""

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set"
    echo ""
    echo "This example requires OpenAI API access for:"
    echo "  - Router: LLM-based intent detection"
    echo "  - Answer Agent: Grounded answer generation"
    echo ""
    echo "Please set your API key:"
    echo "  export OPENAI_API_KEY='your-key-here'"
    echo ""
    exit 1
fi

echo "✓ OPENAI_API_KEY is set"
echo ""

# Start all agents in background
echo "Starting agents..."
echo ""

echo "  1. Knowledge Store (tool for storing facts)..."
python3 knowledge_store.py &
STORE_PID=$!
sleep 2

echo "  2. Answer Agent (RAG-powered question answering)..."
python3 answer_agent.py &
ANSWER_PID=$!
sleep 2

echo "  3. Router (LLM-based intent detection)..."
python3 router.py &
ROUTER_PID=$!

# Give agents more time to complete initialization
sleep 4

echo ""
echo "✓ All agents running!"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Knowledge Management System Ready"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Usage:"
echo ""
echo "  Interactive mode (recommended):"
echo "    python3 client.py"
echo ""
echo "  Single request mode:"
echo "    python3 client.py 'Python was created by Guido van Rossum'"
echo "    python3 client.py 'Who created Python?'"
echo ""
echo "The router will automatically:"
echo "  • Detect if you want to store knowledge or ask a question"
echo "  • Route to the appropriate agent"
echo "  • Return the result"
echo ""
echo "Press Ctrl+C to stop all agents"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping agents...'; kill $STORE_PID $ANSWER_PID $ROUTER_PID 2>/dev/null; exit" INT
wait

