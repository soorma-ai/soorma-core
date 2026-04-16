#!/bin/bash
# Start script for 06-memory-episodic chatbot example

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="06-memory-episodic"
REPO_ROOT="$(cd "$EXAMPLE_DIR/../.." && pwd)"

echo "🚀 Starting 06-memory-episodic chatbot..."
echo ""
echo "This example demonstrates a multi-agent chatbot with:"
echo "  • Episodic Memory (interaction history)"
echo "  • Semantic Memory (knowledge storage)"
echo "  • Working Memory (session state)"
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
echo "🔐 Priming shared example token provider..."
(cd "$REPO_ROOT" && python -m examples.shared.auth "$EXAMPLE_NAME" "$EXAMPLE_DIR") > /dev/null
echo "✓ Example identity bootstrap and token cache ready"
echo ""

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set"
    echo ""
    echo "This example requires OpenAI API access for:"
    echo "  - Router: LLM-based intent classification"
    echo "  - RAG Agent: Context-aware answer generation"
    echo "  - Concierge: Conversation analysis"
    echo ""
    echo "Please set your API key:"
    echo "  export OPENAI_API_KEY='your-key-here'"
    echo ""
    exit 1
fi

echo "✓ OPENAI_API_KEY is set"
echo ""

echo "This chatbot uses 4 agents working together:"
echo "  1. Router (classifies user intent)"
echo "  2. RAG Agent (answers questions with context)"
echo "  3. Concierge (explores conversation history)"
echo "  4. Knowledge Store (saves facts)"
echo ""
echo "Starting all agents..."
echo ""

# Use trap to cleanup background processes
trap 'kill $(jobs -p) 2>/dev/null' EXIT

# Start agents in background
echo "Starting router..."
python3 "$EXAMPLE_DIR/router.py" &
ROUTER_PID=$!
sleep 2

echo "Starting RAG agent..."
python3 "$EXAMPLE_DIR/rag_agent.py" &
RAG_PID=$!
sleep 2

echo "Starting concierge..."
python3 "$EXAMPLE_DIR/concierge.py" &
CONCIERGE_PID=$!
sleep 2

echo "Starting knowledge store..."
python3 "$EXAMPLE_DIR/knowledge_store.py" &
KNOWLEDGE_PID=$!
sleep 2

echo ""
echo "✅ All agents running!"
echo ""
echo "Now start the client in another terminal:"
echo "  cd examples/06-memory-episodic"
echo "  python3 client.py"
echo ""
echo "Or use the low-level utilities:"
echo "  python3 view_history.py         # View conversation history"
echo "  python3 search_memory.py 'query'  # Search past interactions"
echo ""
echo "Press Ctrl+C to stop all agents"
echo ""

# Wait for all background jobs
wait
