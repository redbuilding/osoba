# OhSee Service Setup Scripts

These scripts help you run OhSee backend as a system service, ensuring scheduled tasks execute reliably even when the application isn't manually started.

## Overview

**Problem**: Scheduled tasks only run when the OhSee backend is running. If you close the terminal or restart your computer, scheduled tasks won't execute.

**Solution**: Run OhSee backend as a system service that:
- Starts automatically on boot
- Runs in the background
- Restarts automatically if it crashes
- Optionally wakes your computer for scheduled tasks

## Quick Start

### macOS
```bash
cd scripts
./setup-macos-service.sh
```

### Linux
```bash
cd scripts
sudo ./setup-linux-service.sh
```

### Windows (PowerShell as Administrator)
```powershell
cd scripts
.\setup-windows-service.ps1
```

## What Gets Installed

### macOS (Launch Agent)
- **Location**: `~/Library/LaunchAgents/com.ohsee.backend.plist`
- **Runs as**: Your user account
- **Starts**: Automatically on login
- **Logs**: `/tmp/ohsee-backend.log` and `/tmp/ohsee-backend-error.log`

**Management Commands**:
```bash
# Stop service
launchctl unload ~/Library/LaunchAgents/com.ohsee.backend.plist

# Start service
launchctl load ~/Library/LaunchAgents/com.ohsee.backend.plist

# View logs
tail -f /tmp/ohsee-backend.log
```

### Linux (systemd)
- **Location**: `/etc/systemd/system/ohsee-backend.service`
- **Runs as**: Your user account (via sudo)
- **Starts**: Automatically on boot
- **Logs**: System journal (journalctl)

**Management Commands**:
```bash
# Stop service
sudo systemctl stop ohsee-backend

# Start service
sudo systemctl start ohsee-backend

# Restart service
sudo systemctl restart ohsee-backend

# View logs
sudo journalctl -u ohsee-backend -f

# Disable auto-start
sudo systemctl disable ohsee-backend
```

### Windows (NSSM Service)
- **Service Name**: `OhSeeBackend`
- **Runs as**: Local System account
- **Starts**: Automatically on boot
- **Logs**: `%TEMP%\ohsee-backend.log` and `%TEMP%\ohsee-backend-error.log`

**Management Commands** (PowerShell as Administrator):
```powershell
# Stop service
Stop-Service OhSeeBackend

# Start service
Start-Service OhSeeBackend

# Restart service
Restart-Service OhSeeBackend

# View service status
Get-Service OhSeeBackend

# Uninstall service
.\setup-windows-service.ps1 -Uninstall
```

## Wake Scheduling (Advanced)

### What is Wake Scheduling?

Wake scheduling allows your computer to automatically wake from sleep to run scheduled tasks, then return to sleep afterward.

**Use Cases**:
- Daily reports that must run at specific times
- Overnight data processing
- Scheduled backups or monitoring

**Considerations**:
- Requires administrator/root access
- Drains battery on laptops (use when plugged in)
- May briefly wake the screen and fans

### macOS Wake Scheduling

**Manual Wake Scheduling**:
```bash
# Schedule one-time wake at 2:00 PM today
sudo pmset schedule wake "02/20/26 14:00:00"

# Schedule recurring wake every day at 9 AM
sudo pmset repeat wake MTWRFSU 09:00:00

# View scheduled wakes
pmset -g sched

# Cancel all scheduled wakes
sudo pmset schedule cancelall
```

**Automatic Wake Scheduling**:
The backend will attempt to schedule wake events automatically when you create scheduled tasks. You may be prompted for your password.

### Linux RTC Wake

**Check Hardware Support**:
```bash
cat /sys/class/rtc/rtc0/wakealarm
```

**Manual Wake Scheduling**:
```bash
# Wake in 1 hour
sudo rtcwake -m mem -s 3600

# Wake at specific time (Unix timestamp)
echo 0 | sudo tee /sys/class/rtc/rtc0/wakealarm  # Clear
echo 1708448400 | sudo tee /sys/class/rtc/rtc0/wakealarm  # Set
```

**Note**: RTC wake support varies by hardware. Some systems may not support this feature.

### Windows Task Scheduler Wake

**Enable Wake Timers**:
1. Open Power Options (Control Panel → Power Options)
2. Click "Change plan settings" → "Change advanced power settings"
3. Expand "Sleep" → "Allow wake timers"
4. Set to "Enable"

**Configure Task Wake**:
1. Open Task Scheduler (`taskschd.msc`)
2. Find OhSee-related tasks
3. Right-click → Properties
4. Conditions tab → Check "Wake the computer to run this task"

## Catch-up Logic (No Service Required)

If you don't want to run OhSee as a service, the backend includes **catch-up logic**:

**How it works**:
1. When the backend starts, it checks for overdue scheduled tasks
2. Overdue tasks execute immediately
3. Tasks are marked with delay information (e.g., "delayed 45m")
4. Recurring tasks calculate the next run from the current time (no cascading delays)

**Limitations**:
- Tasks only run when you manually start the backend
- Delays can be significant if the computer was asleep for hours
- No guarantee of execution if you forget to start the app

**Best for**:
- Casual users with flexible scheduling needs
- Development and testing
- Tasks that don't require precise timing

## Troubleshooting

### Service Won't Start

**macOS**:
```bash
# Check logs
tail -f /tmp/ohsee-backend-error.log

# Verify plist syntax
plutil ~/Library/LaunchAgents/com.ohsee.backend.plist

# Check if port 8000 is in use
lsof -i :8000
```

**Linux**:
```bash
# Check service status
sudo systemctl status ohsee-backend

# View detailed logs
sudo journalctl -u ohsee-backend -n 50

# Check if port 8000 is in use
sudo netstat -tulpn | grep 8000
```

**Windows**:
```powershell
# Check service status
Get-Service OhSeeBackend | Format-List *

# View logs
Get-Content $env:TEMP\ohsee-backend-error.log -Tail 50

# Check if port 8000 is in use
netstat -ano | findstr :8000
```

### Environment Variables Not Loading

**macOS**: Add to plist under `<key>EnvironmentVariables</key>`
**Linux**: Check `/etc/systemd/system/ohsee-backend.service` has `EnvironmentFile=-/path/to/.env`
**Windows**: NSSM loads .env automatically, check logs for parsing errors

### Wake Scheduling Not Working

**macOS**:
- Ensure you entered your password when prompted
- Check scheduled wakes: `pmset -g sched`
- Verify "Wake for network access" is enabled in Energy Saver preferences

**Linux**:
- Verify RTC support: `cat /sys/class/rtc/rtc0/wakealarm`
- Check BIOS settings for wake-on-RTC
- Some laptops don't support RTC wake

**Windows**:
- Verify wake timers are enabled in Power Options
- Check Task Scheduler for wake-enabled tasks
- Ensure computer is plugged in (wake on battery may be disabled)

## Uninstalling

### macOS
```bash
launchctl unload ~/Library/LaunchAgents/com.ohsee.backend.plist
rm ~/Library/LaunchAgents/com.ohsee.backend.plist
```

### Linux
```bash
sudo systemctl stop ohsee-backend
sudo systemctl disable ohsee-backend
sudo rm /etc/systemd/system/ohsee-backend.service
sudo systemctl daemon-reload
```

### Windows
```powershell
.\setup-windows-service.ps1 -Uninstall
```

## Security Considerations

- **macOS**: Launch Agent runs as your user (safe)
- **Linux**: Service runs as your user via sudo (safe)
- **Windows**: Service runs as Local System (elevated privileges)

**Recommendations**:
- Keep your `.env` file secure (contains API keys)
- Don't expose port 8000 to the internet without authentication
- Review logs periodically for suspicious activity

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend logs for error messages
3. Open an issue on GitHub with log excerpts
4. Include your OS version and setup method

---

**Note**: These scripts are optional. OhSee works perfectly fine without running as a service if you don't need scheduled tasks or prefer to start it manually.
