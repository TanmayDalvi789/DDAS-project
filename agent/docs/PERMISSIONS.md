# DDAS Agent Permissions

## Overview

The DDAS Agent runs as a local system service with OS-level permissions to monitor downloads and network activity.

## Windows Permissions

### Required

- **Admin Privileges** (Run as Administrator)
  - Needed to monitor system events
  - Needed to integrate with Windows Defender
  - Needed for network monitoring

### Installation

```powershell
# Run as Administrator
.\scripts\install_windows.ps1
```

### Verification

```powershell
# Check if running as admin
$isAdmin = [bool](([System.Security.Principal.WindowsIdentity]::GetCurrent()).groups -match "S-1-5-32-544")
Write-Host "Running as admin: $isAdmin"
```

## Linux Permissions

### Required

- **Root privileges** or **CAP_SYS_ADMIN capability**
  - Needed for system monitoring
  - Needed for network packet inspection

### Installation

```bash
sudo bash ./scripts/install_linux.sh
```

### Verification

```bash
# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Running as root: true"
else
    echo "Running as root: false"
fi
```

## macOS Permissions

### Required

1. **Full Disk Access**
   - System Preferences → Security & Privacy → Full Disk Access
   - Add DDAS Agent to the list

2. **System Extension Approval**
   - macOS requires system extensions to be approved
   - Agent will request approval on first run

3. **Accessibility Permissions**
   - System Preferences → Security & Privacy → Accessibility
   - Add DDAS Agent to the list

### Installation

```bash
bash ./scripts/install_macos.sh
```

### Verification

```bash
# Check Full Disk Access
ls -l ~/Library/Application\ Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.ApplicationRecentDocuments/com.apple.LSSharedFileList.DesktopFolder.sfl*
```

## Permission Validation Strategy

The agent uses **FAIL-CLOSED** approach:

1. **At startup**: Validate all required permissions
2. **If missing**: Raise PermissionError and exit
3. **Never degrade**: Don't run with partial permissions
4. **Clear feedback**: Tell user exactly what's needed

```python
try:
    validator = PermissionValidator()
    validator.validate_all()  # Raises if failed
except PermissionError as e:
    logger.error(f"Permission validation failed: {e}")
    sys.exit(1)  # FAIL-CLOSED
```

## First Run Flow

1. User installs agent
2. Agent checks permissions
3. If missing: Display guidance dialog
4. User grants permissions via system settings
5. User restarts agent
6. Agent validates and starts normally
