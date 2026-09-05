"""Unit tests for api/owner_mode.py -- the domain allowlist that stops any visitor
from triggering the operator's PAT against a target they don't own.
"""

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from api.owner_mode import assert_owner_mode_allowed


def test_rejects_when_allowlist_is_unset():
    with patch.dict(os.environ, {"OWNER_MODE_ALLOWED_DOMAINS": ""}, clear=False):
        with pytest.raises(HTTPException) as exc_info:
            assert_owner_mode_allowed("https://anything.example/")
        assert exc_info.value.status_code == 403


def test_allows_exact_domain_match():
    with patch.dict(os.environ, {"OWNER_MODE_ALLOWED_DOMAINS": "adityakalambe.xyz"}):
        assert_owner_mode_allowed("https://adityakalambe.xyz/")  # should not raise


def test_allows_subdomain_of_allowed_domain():
    with patch.dict(os.environ, {"OWNER_MODE_ALLOWED_DOMAINS": "adityakalambe.xyz"}):
        assert_owner_mode_allowed("https://www.adityakalambe.xyz/")  # should not raise


def test_rejects_unrelated_domain():
    with patch.dict(os.environ, {"OWNER_MODE_ALLOWED_DOMAINS": "adityakalambe.xyz"}):
        with pytest.raises(HTTPException) as exc_info:
            assert_owner_mode_allowed("https://example.com/")
        assert exc_info.value.status_code == 403


def test_rejects_lookalike_domain_suffix_bypass():
    # "notadityakalambe.xyz" ends with the allowed string but is NOT a subdomain of it --
    # must not match via a naive .endswith(allowed_domain) check.
    with patch.dict(os.environ, {"OWNER_MODE_ALLOWED_DOMAINS": "adityakalambe.xyz"}):
        with pytest.raises(HTTPException):
            assert_owner_mode_allowed("https://notadityakalambe.xyz/")


def test_allows_any_domain_in_comma_separated_list():
    with patch.dict(os.environ, {"OWNER_MODE_ALLOWED_DOMAINS": "one.example,two.example"}):
        assert_owner_mode_allowed("https://two.example/")  # should not raise
