#!/bin/bash
# OhSee Linux Service Setup Script (systemd)
# This script sets up OhSee backend as a systemd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
SERVICE_NAME="ohsee-backend"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

echo "🔍 OhSee Linux Service Setup (systemd)"
echo "======================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ Error: Backend directory not found at $BACKEND_DIR"
    exit 1
fi

# Find Python and uvicorn
PYTHON_PATH=$(which python3 || which python)
UVICORN_PATH=$(which uvicorn)
CURRENT_USER="${SUDO_USER:-$USER}"

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
echo "✓ Running as user: $CURRENT_USER"
echo ""

# Check if .env file exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "⚠️  Warning: .env file not found at $BACKEND_DIR/.env"
    echo "   The service may not start without proper configuration."
    echo ""
fi

# Create the systemd service file
echo "📝 Creating systemd service..."
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=OhSee Backend Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$BACKEND_DIR

# Environment
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=-$BACKEND_DIR/.env

# Command
ExecStart=$UVICORN_PATH main:app --host 0.0.0.0 --port 8000

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Created systemd service at $SERVICE_FILE"
echo ""

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload
echo "✓ Systemd reloaded"
echo ""

# Enable and start the service
echo "🚀 Enabling and starting service..."
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME
echo "✓ Service enabled and started"
echo ""

# Check status
sleep 2
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ OhSee backend is now running as a system service!"
    echo ""
    echo "📊 Service Status:"
    systemctl status $SERVICE_NAME --no-pager -l
    echo ""
    echo "   • Backend URL: http://localhost:8000"
    echo ""
else
    echo "⚠️  Service may not have started. Check logs:"
    echo "   sudo journalctl -u $SERVICE_NAME -f"
    exit 1
fi

# Ask about RTC wake scheduling
echo "⏰ RTC Wake Scheduling (Optional)"
echo "================================="
echo ""
echo "Would you like information about enabling RTC wake for scheduled tasks?"
echo "This allows your system to wake from sleep to run scheduled tasks."
echo ""
read -p "Show RTC wake information? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "📝 RTC Wake Setup:"
    echo ""
    echo "1. Check if your hardware supports RTC wake:"
    echo "   cat /sys/class/rtc/rtc0/wakealarm"
    echo ""
    echo "2. To schedule a wake event (requires root):"
    echo "   # Clear existing alarm"
    echo "   echo 0 | sudo tee /sys/class/rtc/rtc0/wakealarm"
    echo "   # Set new alarm (Unix timestamp)"
    echo "   echo 1708448400 | sudo tee /sys/class/rtc/rtc0/wakealarm"
    echo ""
    echo "3. Or use rtcwake utility:"
    echo "   sudo rtcwake -m mem -s 3600  # Wake in 1 hour"
    echo ""
    echo "⚠️  Note: RTC wake requires root access and hardware support."
    echo "   The backend will attempt to schedule wake events automatically"
    echo "   if you grant it the necessary permissions."
    echo ""
else
    echo ""
    echo "ℹ️  RTC wake not configured."
    echo "   Scheduled tasks will only run when your system is awake."
fi

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "Useful commands:"
echo "  • View logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "  • Stop service: sudo systemctl stop $SERVICE_NAME"
echo "  • Start service: sudo systemctl start $SERVICE_NAME"
echo "  • Restart:      sudo systemctl restart $SERVICE_NAME"
echo "  • Disable:      sudo systemctl disable $SERVICE_NAME"
echo ""
echo "Next steps:"
echo "  1. Start the frontend: cd frontend && npm run dev"
echo "  2. Open http://localhost:5173"
echo "  3. Schedule tasks in the Tasks panel"
echo ""
