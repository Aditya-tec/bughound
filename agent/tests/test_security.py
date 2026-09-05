"""Unit tests for agent/security.py -- the second, independent SSRF check that runs
right before the crawler connects (defense in depth against DNS rebinding between
job creation and scan time). Deliberately mirrors api/tests/test_security.py since
these are two independently-maintained copies by design, not shared code.
"""

import socket
from unittest.mock import patch

import pytest

from security import MAX_TARGET_URL_LENGTH, SSRFValidationError, validate_public_target


def _addrinfo(ip: str):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]


def test_rejects_non_http_scheme():
    with pytest.raises(SSRFValidationError, match="http or https"):
        validate_public_target("file:///etc/passwd")


def test_rejects_localhost_without_dns_lookup():
    with patch("security.socket.getaddrinfo", side_effect=AssertionError("should not resolve")):
        with pytest.raises(SSRFValidationError):
            validate_public_target("http://localhost:5432")


def test_rejects_cloud_metadata_ip():
    with patch("security.socket.getaddrinfo", return_value=_addrinfo("169.254.169.254")):
        with pytest.raises(SSRFValidationError, match="non-public address"):
            validate_public_target("http://169.254.169.254/latest/meta-data/")


def test_rejects_private_ip():
    with patch("security.socket.getaddrinfo", return_value=_addrinfo("10.0.0.5")):
        with pytest.raises(SSRFValidationError, match="non-public address"):
            validate_public_target("http://internal.example/")


def test_rejects_url_over_length_cap():
    long_url = "https://example.com/" + "a" * MAX_TARGET_URL_LENGTH
    with pytest.raises(SSRFValidationError, match="exceeds"):
        validate_public_target(long_url)


def test_allows_public_ip():
    with patch("security.socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
        validate_public_target("https://example.com/")  # should not raise
