"""CLI entry point for Focus Blocker."""

import sys
import signal

from dns_server import FocusBlockerDNS, IS_WINDOWS
from scheduler import get_status_message
from installer import install, uninstall, get_status

ELEVATION_CMD = "Run as Administrator" if IS_WINDOWS else "sudo python"


def print_usage():
    """Print usage information."""
    print(
        f"""Focus Blocker - Block distracting websites

Usage:
    {ELEVATION_CMD} main.py <command>

Commands:
    start      Start the DNS server (foreground)
    install    Install as a startup service (runs on boot)
    uninstall  Remove from startup
    status     Show current blocking status

Examples:
    {ELEVATION_CMD} main.py install
    {ELEVATION_CMD} main.py uninstall
    python main.py status

DNS settings are automatically maintained when switching networks.
"""
    )


def cmd_start():
    """Start the DNS server in foreground."""
    server = FocusBlockerDNS()

    def signal_handler(signum, frame):
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server.start()
    except PermissionError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except OSError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_install():
    """Install as startup service."""
    success = install()
    sys.exit(0 if success else 1)


def cmd_uninstall():
    """Uninstall startup service."""
    success = uninstall()
    sys.exit(0 if success else 1)


def cmd_status():
    """Show current status."""
    status = get_status()

    print("=" * 50)
    print("Focus Blocker Status")
    print("=" * 50)
    print()
    print(f"Installed: {'Yes' if status['installed'] else 'No'}")
    print(f"Running:   {'Yes' if status['running'] else 'No'}")
    print()
    print(get_status_message())
    print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    commands = {
        "start": cmd_start,
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "status": cmd_status,
    }

    if command in commands:
        commands[command]()
    elif command in ("-h", "--help", "help"):
        print_usage()
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
