"""Unit tests for api/security.py -- the SSRF guard checked at job-creation time.

Mocks socket.getaddrinfo so these are fast and deterministic in CI regardless of
network conditions, rather than depending on live DNS resolution.
"""

import socket
from unittest.mock import patch

import pytest

from api.security import MAX_TARGET_URL_LENGTH, SSRFValidationError, validate_public_target


def _addrinfo(ip: str):
    """Builds a minimal getaddrinfo()-shaped return value for a single IPv4 address."""
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]


def test_rejects_non_http_scheme():
    with pytest.raises(SSRFValidationError, match="http or https"):
        validate_public_target("ftp://example.com/")


def test_rejects_missing_hostname():
    with pytest.raises(SSRFValidationError, match="hostname"):
        validate_public_target("https:///path")


def test_rejects_localhost_without_dns_lookup():
    # Must be rejected by the hostname blocklist, not by DNS resolution --
    # if getaddrinfo were called and not mocked, this test would be flaky.
    with patch("api.security.socket.getaddrinfo", side_effect=AssertionError("should not resolve")):
        with pytest.raises(SSRFValidationError, match="not a scannable public target"):
            validate_public_target("http://localhost/")


def test_rejects_dot_local_suffix():
    with patch("api.security.socket.getaddrinfo", side_effect=AssertionError("should not resolve")):
        with pytest.raises(SSRFValidationError):
            validate_public_target("http://printer.local/")


def test_rejects_cloud_metadata_ip():
    with patch("api.security.socket.getaddrinfo", return_value=_addrinfo("169.254.169.254")):
        with pytest.raises(SSRFValidationError, match="non-public address"):
            validate_public_target("http://metadata.example/")


def test_rejects_private_ip():
    with patch("api.security.socket.getaddrinfo", return_value=_addrinfo("192.168.1.1")):
        with pytest.raises(SSRFValidationError, match="non-public address"):
            validate_public_target("http://internal.example/")


def test_rejects_loopback_ip():
    with patch("api.security.socket.getaddrinfo", return_value=_addrinfo("127.0.0.1")):
        with pytest.raises(SSRFValidationError, match="non-public address"):
            validate_public_target("http://loopback.example/")


def test_rejects_unresolvable_host():
    with patch("api.security.socket.getaddrinfo", side_effect=socket.gaierror("no such host")):
        with pytest.raises(SSRFValidationError, match="Could not resolve"):
            validate_public_target("https://this-does-not-resolve.example/")


def test_rejects_url_over_length_cap():
    long_url = "https://example.com/" + "a" * (MAX_TARGET_URL_LENGTH)
    with pytest.raises(SSRFValidationError, match="exceeds"):
        validate_public_target(long_url)


def test_allows_public_ip():
    with patch("api.security.socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
        validate_public_target("https://example.com/")  # should not raise
