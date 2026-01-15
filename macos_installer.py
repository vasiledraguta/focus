"""macOS LaunchDaemon installer for Focus Blocker."""

import os
import sys
import subprocess
from pathlib import Path

PLIST_NAME = "com.focus.blocker.plist"
PLIST_PATH = Path(f"/Library/LaunchDaemons/{PLIST_NAME}")


def get_python_path() -> str:
    """Get the full path to the current Python interpreter."""
    return sys.executable


def get_project_path() -> Path:
    """Get the project root directory (where main.py lives)."""
    return Path(__file__).parent.resolve()


def create_plist_content() -> str:
    """Generate the LaunchDaemon plist content."""
    python_path = get_python_path()
    project_path = get_project_path()

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.focus.blocker</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{project_path}/main.py</string>
        <string>start</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{project_path}</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/tmp/focus_blocker.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/focus_blocker.error.log</string>
</dict>
</plist>
"""


def install() -> bool:
    """Install the LaunchDaemon."""
    if os.geteuid() != 0:
        print("Error: Installation requires root privileges. Run with sudo.")
        return False

    # Stop existing service if running
    if PLIST_PATH.exists():
        print("Stopping existing service...")
        subprocess.run(
            ["launchctl", "bootout", f"system/{PLIST_NAME.replace('.plist', '')}"],
            capture_output=True,
        )

    # Write plist file
    plist_content = create_plist_content()
    try:
        PLIST_PATH.write_text(plist_content)
        os.chmod(PLIST_PATH, 0o644)
        os.chown(PLIST_PATH, 0, 0)  # root:wheel
    except Exception as e:
        print(f"Error writing plist: {e}")
        return False

    # Bootstrap the service (modern launchctl method that survives reboots)
    # First, try to bootout in case it's already loaded
    subprocess.run(
        ["launchctl", "bootout", f"system/{PLIST_NAME.replace('.plist', '')}"],
        capture_output=True,
    )
    
    result = subprocess.run(
        ["launchctl", "bootstrap", "system", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error bootstrapping service: {result.stderr}")
        return False

    # Configure system DNS to use our local DNS server
    print("Configuring system DNS to use Focus Blocker...")
    dns_result = subprocess.run(
        ["networksetup", "-setdnsservers", "Wi-Fi", "127.0.0.1"],
        capture_output=True,
        text=True,
    )
    
    if dns_result.returncode != 0:
        print(f"Warning: Could not set DNS automatically: {dns_result.stderr}")
        print("Please run manually: sudo networksetup -setdnsservers Wi-Fi 127.0.0.1")
    
    print("Focus Blocker installed successfully!")
    print("\nThe DNS server will start automatically on boot.")

    return True


def uninstall() -> bool:
    """Uninstall the LaunchDaemon."""
    if os.geteuid() != 0:
        print("Error: Uninstallation requires root privileges. Run with sudo.")
        return False

    if not PLIST_PATH.exists():
        print("Focus Blocker is not installed.")
        return True

    # Bootout the service (modern launchctl method)
    subprocess.run(
        ["launchctl", "bootout", f"system/{PLIST_NAME.replace('.plist', '')}"],
        capture_output=True,
        text=True,
    )

    # Remove plist file
    try:
        PLIST_PATH.unlink()
    except Exception as e:
        print(f"Error removing plist: {e}")
        return False

    # Reset DNS settings to default (Empty)
    print("Resetting DNS settings to default...")
    subprocess.run(
        ["networksetup", "-setdnsservers", "Wi-Fi", "Empty"], capture_output=True
    )

    print("Focus Blocker uninstalled successfully.")
    return True


def is_installed() -> bool:
    """Check if Focus Blocker is installed as a LaunchDaemon."""
    return PLIST_PATH.exists()


def is_running() -> bool:
    """Check if the Focus Blocker service is running."""
    result = subprocess.run(
        ["launchctl", "print", "system/com.focus.blocker"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def get_status() -> dict:
    """Get the current status of Focus Blocker."""
    return {
        "installed": is_installed(),
        "running": is_running(),
        "plist_path": str(PLIST_PATH),
    }
