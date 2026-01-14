"""CLI entry point for Focus Blocker."""

import sys
import signal

from dns_server import FocusBlockerDNS
from scheduler import get_status_message
from installer import install, uninstall, get_status


def print_usage():
    """Print usage information."""
    print(
        """Focus Blocker - Block distracting websites

Usage:
    sudo python main.py <command>

Commands:
    start      Start the DNS server (foreground)
    install    Install as a startup daemon (runs on boot)
    uninstall  Remove from startup
    status     Show current blocking status

Examples:
    # Install and run at startup
    sudo python main.py install
    
    # Check status
    sudo python main.py status
    
    # Remove from startup
    sudo python main.py uninstall
"""
    )


def cmd_start():
    """Start the DNS server in foreground."""
    server = FocusBlockerDNS()

    def signal_handler(signum, frame):
        print("\nShutting down...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server.start()
    except PermissionError as e:
        print(f"Error: {e}")
        print("Hint: Run with sudo to bind to port 53")
        sys.exit(1)
    except OSError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_install():
    """Install as LaunchDaemon."""
    success = install()
    sys.exit(0 if success else 1)


def cmd_uninstall():
    """Uninstall LaunchDaemon."""
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
