"""SSRF guard for scan targets.

The agent runs inside a GitHub Actions runner -- a real cloud VM with its own
metadata service -- so an unvalidated target_url is a real SSRF vector, not a
theoretical one. This is checked here (job creation) and again in
agent/security.py right before the crawler connects, since a hostname's DNS
answer can change between the two checks (DNS rebinding).
"""

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}
BLOCKED_HOSTNAME_SUFFIXES = (".local", ".internal")


class SSRFValidationError(ValueError):
    """Raised when a target URL is not a safe, publicly-routable scan target."""


def validate_public_target(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFValidationError("Target URL must use http or https")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise SSRFValidationError("Target URL must include a hostname")
    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(BLOCKED_HOSTNAME_SUFFIXES):
        raise SSRFValidationError(f"Host '{hostname}' is not a scannable public target")

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise SSRFValidationError(f"Could not resolve host '{hostname}'") from exc
    if not infos:
        raise SSRFValidationError(f"Could not resolve host '{hostname}'")

    for _family, _type, _proto, _canon, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise SSRFValidationError(
                f"Host '{hostname}' resolves to a non-public address ({ip}) and cannot be scanned"
            )
