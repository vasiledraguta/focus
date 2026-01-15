"""macOS LaunchDaemon installer for Focus Blocker."""

import os
import sys
import subprocess
from pathlib import Path

PLIST_NAME = "com.focus.blocker.plist"
PLIST_PATH = Path(f"/Library/LaunchDaemons/{PLIST_NAME}")
RESOLVER_DIR = Path("/etc/resolver")

# TLDs for resolver files (covers most websites)
TLDS = [
    "com",
    "net",
    "org",
    "io",
    "co",
    "app",
    "dev",
    "me",
    "tv",
    "gg",
    "edu",
    "gov",
    "mil",
    "info",
    "biz",
    "name",
    "pro",
    "uk",
    "de",
    "fr",
    "es",
    "it",
    "nl",
    "ru",
    "cn",
    "jp",
    "kr",
    "au",
    "ca",
    "br",
    "in",
    "mx",
    "pl",
    "se",
    "no",
    "fi",
    "dk",
    "ch",
    "at",
    "be",
    "pt",
    "cz",
    "hu",
    "ro",
    "bg",
    "hr",
    "sk",
    "si",
    "lt",
    "lv",
    "ee",
    "ie",
    "gr",
    "il",
    "ae",
    "sa",
    "za",
    "nz",
    "ar",
    "cl",
    "co",
    "xyz",
    "online",
    "site",
    "tech",
    "store",
    "blog",
    "cloud",
    "live",
    "social",
    "video",
    "news",
    "media",
    "music",
    "game",
    "games",
]


def get_network_services() -> list[str]:
    """Get all network services (excluding disabled ones)."""
    result = subprocess.run(
        ["networksetup", "-listallnetworkservices"],
        capture_output=True,
        text=True,
    )
    services = []
    for line in result.stdout.strip().split("\n"):
        # Skip header line and disabled services (marked with *)
        if line and not line.startswith("An asterisk") and not line.startswith("*"):
            services.append(line)
    return services


def set_dns_all_services(dns_server: str) -> None:
    """Set DNS server for all network services."""
    services = get_network_services()
    for service in services:
        subprocess.run(
            ["networksetup", "-setdnsservers", service, dns_server],
            capture_output=True,
        )
        print(f"  Configured DNS for: {service}")


def setup_resolver_files(dns_server: str) -> None:
    """Set up /etc/resolver/ files to redirect DNS queries."""
    RESOLVER_DIR.mkdir(mode=0o755, exist_ok=True)

    for tld in TLDS:
        resolver_file = RESOLVER_DIR / tld
        resolver_file.write_text(f"nameserver {dns_server}\n")
        os.chmod(resolver_file, 0o644)
        print(f"  Created resolver for: .{tld}")


def cleanup_resolver_files() -> None:
    """Remove /etc/resolver/ files we created."""
    for tld in TLDS:
        resolver_file = RESOLVER_DIR / tld
        if resolver_file.exists():
            resolver_file.unlink()
            print(f"  Removed resolver for: .{tld}")


def flush_dns_cache() -> None:
    """Flush DNS cache."""
    subprocess.run(["dscacheutil", "-flushcache"], capture_output=True)
    subprocess.run(["killall", "-HUP", "mDNSResponder"], capture_output=True)
    print("  Flushed DNS cache")


def configure_system_dns() -> None:
    """Configure system-wide DNS using resolver files and network services."""
    # Method 1: Set up resolver files (persists across network changes)
    print("  Setting up resolver files...")
    setup_resolver_files("127.0.0.1")

    # Method 2: Also set network service DNS (for immediate effect)
    set_dns_all_services("127.0.0.1")

    flush_dns_cache()


def reset_system_dns() -> None:
    """Reset DNS settings to defaults."""
    # Remove resolver files
    print("  Cleaning up resolver files...")
    cleanup_resolver_files()

    # Reset network service DNS
    set_dns_all_services("Empty")

    flush_dns_cache()


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

    # Configure system DNS to use our local DNS server for all network services
    print("Configuring system DNS to use Focus Blocker...")
    configure_system_dns()

    print("\nFocus Blocker installed successfully!")
    print("The DNS server will start automatically on boot.")
    print("\nDNS settings will be automatically maintained when you switch networks.")

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

    # Reset DNS settings to default for all network services
    print("Resetting DNS settings to default...")
    reset_system_dns()

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
