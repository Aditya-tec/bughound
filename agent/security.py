"""SSRF guard for scan targets.

This runner IS the cloud VM with its own metadata service, so this is the
second, independent check: api/security.py already validated target_url at
job-creation time, but a hostname's DNS answer can change between then and
now (DNS rebinding), so it's re-resolved and re-checked right before the
crawler actually connects.
"""

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}
BLOCKED_HOSTNAME_SUFFIXES = (".local", ".internal")
MAX_TARGET_URL_LENGTH = 2048  # practical browser/server URL length convention


class SSRFValidationError(ValueError):
    """Raised when a target URL is not a safe, publicly-routable scan target."""


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def is_public_hostname(hostname: str) -> bool:
    """Boolean version of the same check, for use in a per-request route guard where
    raising isn't convenient (see install_ssrf_route_guard in crawler.py) -- resolves
    the hostname and returns False if it's blocklisted or resolves anywhere private."""
    hostname = hostname.lower()
    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(BLOCKED_HOSTNAME_SUFFIXES):
        return False
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    return not any(_is_blocked_ip(ipaddress.ip_address(sockaddr[0])) for *_, sockaddr in infos)


def validate_public_target(url: str) -> None:
    if len(url) > MAX_TARGET_URL_LENGTH:
        raise SSRFValidationError(f"Target URL exceeds {MAX_TARGET_URL_LENGTH} characters")

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
        if _is_blocked_ip(ip):
            raise SSRFValidationError(
                f"Host '{hostname}' resolves to a non-public address ({ip}) and cannot be scanned"
            )
