#!/bin/bash
# OhSee macOS Service Setup Script
# This script sets up OhSee backend as a Launch Agent with optional wake scheduling

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.ohsee.backend.plist"
PLIST_PATH="$LAUNCH_AGENT_DIR/$PLIST_NAME"

echo "🔍 OhSee macOS Service Setup"
echo "=============================="
echo ""

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ Error: Backend directory not found at $BACKEND_DIR"
    exit 1
fi

# Find Python and uvicorn
PYTHON_PATH=$(which python3 || which python)
UVICORN_PATH=$(which uvicorn)

if [ -z "$PYTHON_PATH" ]; then
    echo "❌ Error: Python not found. Please install Python 3.11+"
    exit 1
fi

if [ -z "$UVICORN_PATH" ]; then
    echo "❌ Error: uvicorn not found. Please install: pip install uvicorn"
    exit 1
fi

echo "✓ Found Python: $PYTHON_PATH"
echo "✓ Found uvicorn: $UVICORN_PATH"
echo ""

# Create Launch Agent directory if it doesn't exist
mkdir -p "$LAUNCH_AGENT_DIR"

# Create the plist file
echo "📝 Creating Launch Agent configuration..."
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ohsee.backend</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$UVICORN_PATH</string>
        <string>main:app</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$BACKEND_DIR</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/tmp/ohsee-backend.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/ohsee-backend-error.log</string>
</dict>
</plist>
EOF

echo "✓ Created Launch Agent at $PLIST_PATH"
echo ""

# Load the Launch Agent
echo "🚀 Loading Launch Agent..."
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
echo "✓ Launch Agent loaded"
echo ""

# Check if it's running
sleep 2
if launchctl list | grep -q "com.ohsee.backend"; then
    echo "✅ OhSee backend is now running as a background service!"
    echo ""
    echo "📊 Service Status:"
    echo "   • Backend URL: http://localhost:8000"
    echo "   • Logs: /tmp/ohsee-backend.log"
    echo "   • Errors: /tmp/ohsee-backend-error.log"
    echo ""
else
    echo "⚠️  Service may not have started. Check logs:"
    echo "   tail -f /tmp/ohsee-backend-error.log"
    exit 1
fi

# Ask about wake scheduling
echo "⏰ Wake Scheduling (Optional)"
echo "=============================="
echo ""
echo "Would you like to enable wake scheduling for scheduled tasks?"
echo "This allows your Mac to wake from sleep to run scheduled tasks."
echo ""
echo "⚠️  Note: This requires sudo access and will drain battery on laptops."
echo ""
read -p "Enable wake scheduling? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "📝 Wake scheduling must be configured per scheduled task."
    echo "   The backend will attempt to schedule wake events automatically."
    echo ""
    echo "⚠️  You may be prompted for your password when tasks are scheduled."
    echo ""
    echo "To manually schedule a wake event:"
    echo "   sudo pmset schedule wake \"MM/DD/YY HH:MM:SS\""
    echo ""
    echo "To view scheduled wake events:"
    echo "   pmset -g sched"
    echo ""
    echo "✓ Wake scheduling information provided"
else
    echo ""
    echo "ℹ️  Wake scheduling not enabled."
    echo "   Scheduled tasks will only run when your Mac is awake."
    echo "   You can enable this later by running this script again."
fi

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "Next steps:"
echo "  1. Start the frontend: cd frontend && npm run dev"
echo "  2. Open http://localhost:5173"
echo "  3. Schedule tasks in the Tasks panel"
echo ""
echo "To stop the service:"
echo "  launchctl unload $PLIST_PATH"
echo ""
echo "To restart the service:"
echo "  launchctl unload $PLIST_PATH && launchctl load $PLIST_PATH"
echo ""
