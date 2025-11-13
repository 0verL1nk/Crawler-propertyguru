#!/bin/bash

# Load environment variables from .env file (removing comments)
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env..."
    export $(grep -v '^#' .env | grep -v '^$' | sed 's/#.*$//' | xargs)
    echo "✅ Environment variables loaded"
else
    echo "❌ .env file not found!"
    exit 1
fi

# Display AI configuration
echo ""
echo "🤖 AI Configuration:"
echo "   OPENAI_API_BASE: $OPENAI_API_BASE"
echo "   OPENAI_CHAT_MODEL: $OPENAI_CHAT_MODEL"
echo "   OPENAI_CHAT_EXTRA_BODY: $OPENAI_CHAT_EXTRA_BODY"
echo ""

# Stop old server
if pgrep -f "searcher" > /dev/null; then
    echo "🛑 Stopping old server..."
    pkill -f "searcher"
    sleep 2
fi

# Start new server
echo "🚀 Starting server..."
./build/searcher

