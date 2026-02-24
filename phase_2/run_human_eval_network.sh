#!/bin/bash
# Network deployment script for Human Evaluation Streamlit App
# Allows other computers on the same network to access the app

cd "$(dirname "$0")"

echo "🌐 Starting Human Evaluation Interface (Network Mode)..."
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

# Get local IP address
echo "🔍 Detecting local IP addresses..."
echo ""

if command -v ip &> /dev/null; then
    # Linux with ip command
    LOCAL_IP=$(ip route get 1 | awk '{print $7; exit}')
elif command -v hostname &> /dev/null; then
    # Try hostname command
    LOCAL_IP=$(hostname -I | awk '{print $1}')
else
    LOCAL_IP="Unable to detect"
fi

echo "════════════════════════════════════════════════════════"
echo "✅ Server will be accessible at:"
echo ""
echo "   📱 On this computer:"
echo "      http://localhost:8501"
echo ""
echo "   🌐 On other computers in the same network:"
echo "      http://${LOCAL_IP}:8501"
echo ""
echo "════════════════════════════════════════════════════════"
echo ""
echo "📝 Share the network URL with your team members"
echo "🔒 Make sure they are on the same WiFi/Network"
echo "💾 All evaluations will be saved to this computer's CSV file"
echo ""
echo "Press Ctrl+C to stop the server"
echo "════════════════════════════════════════════════════════"
echo ""

# Launch Streamlit with network access enabled
streamlit run human_eval_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false

