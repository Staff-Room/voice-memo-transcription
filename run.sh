#!/bin/bash

# Voice Memo Transcription Launcher Script
# Activates the virtual environment and runs the voice memo processor

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import whisper" 2>/dev/null; then
    echo "❌ Whisper not installed. Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the voice memo processor
echo "🎙️ Starting Voice Memo Processor..."
echo ""

# Pass all arguments to the script
python voice_memo_processor.py "$@"

echo ""
echo "✨ Voice Memo Processor finished."