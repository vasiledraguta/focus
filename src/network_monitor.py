"""Network change monitor for automatic DNS configuration on macOS."""

import re
import subprocess
import threading
import time
from typing import Callable, Optional


def get_current_dns_from_scutil() -> list[str]:
    """Get current DNS servers using scutil."""
    result = subprocess.run(
        ["scutil", "--dns"],
        capture_output=True,
        text=True,
    )

    dns_servers = []
    in_resolver = False

    for line in result.stdout.split("\n"):
        line = line.strip()
        if line.startswith("resolver #1"):
            in_resolver = True
        elif line.startswith("resolver #") and in_resolver:
            break  # Only care about primary resolver
        elif in_resolver and line.startswith("nameserver["):
            # Extract IP from "nameserver[0] : 127.0.0.1"
            if ":" in line:
                ip = line.split(":")[-1].strip()
                if ip:
                    dns_servers.append(ip)

    return dns_servers


def set_dns_via_scutil(dns_server: str) -> bool:
    """Set DNS server using scutil (works when running as root)."""
    # Create scutil commands to set DNS
    scutil_commands = f"""
d.init
d.add ServerAddresses * {dns_server}
set State:/Network/Service/focus_blocker/DNS
set Setup:/Network/Service/focus_blocker/DNS
d.init
d.add ServerAddresses * {dns_server}
set State:/Network/Global/DNS
quit
"""

    result = subprocess.run(
        ["scutil"],
        input=scutil_commands,
        capture_output=True,
        text=True,
    )

    return result.returncode == 0


def get_primary_service_id() -> Optional[str]:
    """Get the primary network service ID."""
    result = subprocess.run(
        ["scutil"],
        input="show State:/Network/Global/IPv4\nquit\n",
        capture_output=True,
        text=True,
    )

    service_id = None
    for line in result.stdout.split("\n"):
        if "PrimaryService" in line:
            # Extract service ID from "PrimaryService : XXXXXXXX-XXXX-..."
            if ":" in line:
                service_id = line.split(":")[-1].strip()
                break

    return service_id


def set_dns_for_service(service_id: str, dns_server: str) -> bool:
    """Set DNS for a specific service ID using scutil."""
    scutil_commands = f"""
d.init
d.add ServerAddresses * {dns_server}
set State:/Network/Service/{service_id}/DNS
quit
"""

    result = subprocess.run(
        ["scutil"],
        input=scutil_commands,
        capture_output=True,
        text=True,
    )

    return result.returncode == 0


def flush_dns_cache() -> None:
    """Flush the system DNS cache."""
    subprocess.run(["dscacheutil", "-flushcache"], capture_output=True)
    subprocess.run(["killall", "-HUP", "mDNSResponder"], capture_output=True)


def get_active_interface() -> Optional[str]:
    """Get the currently active network interface."""
    result = subprocess.run(
        ["route", "-n", "get", "default"],
        capture_output=True,
        text=True,
    )

    for line in result.stdout.split("\n"):
        if "interface:" in line.lower():
            return line.split(":")[-1].strip()

    return None


def get_dhcp_dns_servers() -> list[str]:
    """Get DNS servers from DHCP lease (the network's actual DNS)."""
    interface = get_active_interface()
    if not interface:
        return []

    result = subprocess.run(
        ["ipconfig", "getpacket", interface],
        capture_output=True,
        text=True,
    )

    dns_servers = []
    for line in result.stdout.split("\n"):
        # Look for domain_name_server line like: domain_name_server (ip_mult): {172.30.240.1}
        if "domain_name_server" in line:
            # Extract IPs from between { }
            ips = re.findall(r"(\d+\.\d+\.\d+\.\d+)", line)
            dns_servers.extend(ips)

    return dns_servers


def is_dns_configured(dns_server: str) -> bool:
    """Check if DNS is currently configured to use our server."""
    current_dns = get_current_dns_from_scutil()
    return dns_server in current_dns


class NetworkMonitor:
    """Monitors network changes and automatically configures DNS."""

    # Class variable to store original DNS servers discovered before we override them
    original_upstream_dns: list[str] = []

    def __init__(
        self,
        dns_server: str = "127.0.0.1",
        check_interval: float = 15.0,
        on_reconfigure: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the network monitor.

        Args:
            dns_server: The DNS server address to configure (default: 127.0.0.1)
            check_interval: How often to check DNS settings in seconds (default: 15.0)
            on_reconfigure: Optional callback when DNS is reconfigured
        """
        self.dns_server = dns_server
        self.check_interval = check_interval
        self.on_reconfigure = on_reconfigure

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_interface: Optional[str] = None
        self._last_service_id: Optional[str] = None

        # Capture original DNS servers before we override them
        self._capture_original_dns()

    def _capture_original_dns(self) -> None:
        """Capture the network's original DNS servers before we override them."""
        # Primary source: DHCP-provided DNS (always accurate, even if we've already overridden)
        dhcp_dns = get_dhcp_dns_servers()
        if dhcp_dns:
            NetworkMonitor.original_upstream_dns = dhcp_dns
            return

        # Fallback: current scutil DNS (only if not already set to localhost)
        current_dns = get_current_dns_from_scutil()
        original = [
            dns
            for dns in current_dns
            if dns != self.dns_server and not dns.startswith("127.")
        ]
        if original:
            NetworkMonitor.original_upstream_dns = original

    def _configure_dns(self) -> bool:
        """Configure DNS to use our server."""
        success = False

        # Method 1: Set global DNS
        global_success = set_dns_via_scutil(self.dns_server)
        if global_success:
            success = True

        # Method 2: Set DNS for primary service
        service_id = get_primary_service_id()
        service_success = False
        if service_id:
            service_success = set_dns_for_service(service_id, self.dns_server)
            if service_success:
                success = True
                self._last_service_id = service_id

        if success:
            flush_dns_cache()
            if self.on_reconfigure:
                self.on_reconfigure(service_id or "global")

        return success

    def _check_and_configure_dns(self) -> None:
        """Check DNS settings and reconfigure if needed."""
        current_interface = get_active_interface()
        current_service_id = get_primary_service_id()

        # Detect network changes
        interface_changed = (
            current_interface is not None and current_interface != self._last_interface
        )
        service_changed = (
            current_service_id is not None
            and current_service_id != self._last_service_id
        )

        # Check if DNS needs configuration
        dns_correct = is_dns_configured(self.dns_server)

        if not dns_correct or interface_changed or service_changed:
            self._configure_dns()

        # Update state
        self._last_interface = current_interface
        if current_service_id:
            self._last_service_id = current_service_id

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        # Initial configuration
        self._configure_dns()

        while self._running:
            time.sleep(self.check_interval)
            if self._running:
                try:
                    self._check_and_configure_dns()
                except Exception:
                    # Silently continue on errors to keep monitoring
                    pass

    def start(self) -> None:
        """Start the network monitor in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the network monitor."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.check_interval + 1)
            self._thread = None

    def is_running(self) -> bool:
        """Check if the monitor is running."""
        return self._running and self._thread is not None and self._thread.is_alive()
