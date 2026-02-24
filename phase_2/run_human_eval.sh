#!/bin/bash
# Quick launch script for the Human Evaluation Streamlit App

# Navigate to the phase_2 directory
cd "$(dirname "$0")"

echo "🚀 Starting Human Evaluation Interface..."
echo "📍 Current directory: $(pwd)"
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null
then
    echo "❌ Streamlit is not installed."
    echo "Install it with: pip install streamlit pandas"
    exit 1
fi

# Check if the CSV file exists
if [ ! -f "merged_small_scale_summaries_20260224_014339.csv" ]; then
    echo "⚠️  Warning: merged_small_scale_summaries_20260224_014339.csv not found"
    echo "Please ensure the data file is in the current directory."
fi

# Launch the Streamlit app
echo "✅ Launching Streamlit app..."
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run human_eval_app.py --server.port 8501 --server.headless false
