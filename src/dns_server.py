"""DNS server with blocking capabilities."""

import socket
import sys
from typing import Optional

from dnslib import DNSRecord, QTYPE, RR, A, AAAA

from config import (
    BLOCKED_DOMAINS,
    UPSTREAM_DNS,
    UPSTREAM_DNS_PORT,
    DNS_HOST,
    DNS_PORT,
    BLOCK_IP,
    BLOCK_IPV6,
)
from scheduler import is_blocking_active

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

# Only import network monitor on macOS
if IS_MACOS:
    from network_monitor import NetworkMonitor


class FocusBlockerDNS:
    """DNS server that blocks distracting websites based on time schedule."""

    def __init__(self, host: str = DNS_HOST, port: int = DNS_PORT):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self._network_monitor: Optional["NetworkMonitor"] = None

    def is_domain_blocked(self, domain: str) -> bool:
        """
        Check if a domain should be blocked.

        Matches the domain itself and any subdomains.
        e.g., "www.youtube.com" matches "youtube.com"
        """
        # Remove trailing dot if present (DNS FQDN format)
        domain = domain.rstrip(".").lower()

        for blocked in BLOCKED_DOMAINS:
            # Exact match
            if domain == blocked:
                return True
            # Subdomain match (e.g., www.youtube.com ends with .youtube.com)
            if domain.endswith("." + blocked):
                return True

        return False

    def _get_upstream_dns_servers(self) -> list[str]:
        """Get list of upstream DNS servers to try, preferring network's original DNS."""
        servers = []
        # Try to get original DNS from network monitor (if on macOS)
        if IS_MACOS:
            from network_monitor import NetworkMonitor

            if NetworkMonitor.original_upstream_dns:
                servers.extend(NetworkMonitor.original_upstream_dns)
        # Always include fallback DNS servers
        if UPSTREAM_DNS not in servers:
            servers.append(UPSTREAM_DNS)
        return servers

    def resolve_upstream(self, request: DNSRecord) -> Optional[DNSRecord]:
        """Forward DNS request to upstream server."""
        upstream_servers = self._get_upstream_dns_servers()

        for upstream in upstream_servers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.settimeout(3)  # Shorter timeout since we have fallbacks
                sock.sendto(request.pack(), (upstream, UPSTREAM_DNS_PORT))
                response_data, _ = sock.recvfrom(4096)
                return DNSRecord.parse(response_data)
            except Exception:
                continue
            finally:
                sock.close()

        return None

    def create_blocked_response(self, request: DNSRecord) -> DNSRecord:
        """
        Create a DNS response that blocks the domain.

        - For A queries: return 0.0.0.0
        - For AAAA queries: return ::
        - For other types (HTTPS/SVCB/CNAME/etc): return NXDOMAIN
        """
        reply = request.reply()
        qname = request.q.qname

        qtype = QTYPE[request.q.qtype]
        if qtype == "A":
            reply.add_answer(RR(qname, QTYPE.A, rdata=A(BLOCK_IP), ttl=60))
        elif qtype == "AAAA":
            reply.add_answer(RR(qname, QTYPE.AAAA, rdata=AAAA(BLOCK_IPV6), ttl=60))
        elif qtype == "ANY":
            reply.add_answer(RR(qname, QTYPE.A, rdata=A(BLOCK_IP), ttl=60))
            reply.add_answer(RR(qname, QTYPE.AAAA, rdata=AAAA(BLOCK_IPV6), ttl=60))
        else:
            # Strongest “block”: claim the name doesn't exist for this record type.
            reply.header.rcode = 3  # NXDOMAIN

        return reply

    def handle_request(self, data: bytes, addr: tuple) -> bytes:
        """Handle incoming DNS request."""
        try:
            request = DNSRecord.parse(data)
            qname = str(request.q.qname)

            # Check if domain should be blocked
            if is_blocking_active() and self.is_domain_blocked(qname):
                # Block the domain
                response = self.create_blocked_response(request)
            else:
                # Forward to upstream DNS
                response = self.resolve_upstream(request)
                if response is None:
                    # If upstream fails, return SERVFAIL
                    response = request.reply()
                    response.header.rcode = 2  # SERVFAIL

            return response.pack()

        except Exception:
            # Return SERVFAIL on error
            try:
                request = DNSRecord.parse(data)
                response = request.reply()
                response.header.rcode = 2
                return response.pack()
            except Exception:
                return b""

    def start(self):
        """Start the DNS server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.socket.bind((self.host, self.port))
        except PermissionError:
            hint = "Run as Administrator." if IS_WINDOWS else "Run with sudo."
            raise PermissionError(f"Cannot bind to port {self.port}. {hint}")
        except OSError as e:
            if "Address already in use" in str(e):
                raise OSError(
                    f"Port {self.port} is already in use. "
                    "Another DNS server may be running."
                )
            raise

        self.running = True

        # Start network monitor on macOS to auto-configure DNS on network changes
        if IS_MACOS:
            self._network_monitor = NetworkMonitor(
                dns_server="127.0.0.1",
                check_interval=15.0,  # Check every 15 seconds (balance between responsiveness and battery)
            )
            self._network_monitor.start()

        while self.running:
            try:
                self.socket.settimeout(1.0)
                try:
                    data, addr = self.socket.recvfrom(4096)
                except socket.timeout:
                    continue

                response = self.handle_request(data, addr)
                if response:
                    self.socket.sendto(response, addr)

            except Exception:
                pass

    def stop(self):
        """Stop the DNS server."""
        self.running = False

        # Stop network monitor if running
        if self._network_monitor:
            self._network_monitor.stop()
            self._network_monitor = None

        if self.socket:
            self.socket.close()
            self.socket = None
